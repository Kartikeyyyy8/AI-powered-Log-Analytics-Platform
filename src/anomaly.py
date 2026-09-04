"""Multi-model anomaly detection for LogSense.

LogSense uses the Autoencoder as the PRIMARY anomaly detector.

Primary signal:
    is_anomaly  -> Autoencoder anomaly
    anomaly_score -> Autoencoder reconstruction error

Additional detectors:
    - Isolation Forest
    - HDBSCAN

The 2-of-3 ensemble is retained as a stronger consensus signal for
the Anomalies page.

Overview and Incident Intelligence use the primary Autoencoder signal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.cluster import HDBSCAN
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# Optional / environment-dependent PyTorch import
# ---------------------------------------------------------------------------

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

except Exception as exc:  # pragma: no cover
    # Keep this module importable even when PyTorch is broken/missing.
    # Streamlit can then show a useful error instead of:
    # AttributeError: 'NoneType' object has no attribute 'Module'
    torch = None
    nn = None
    DataLoader = None
    TensorDataset = None
    TORCH_IMPORT_ERROR = exc

else:
    TORCH_IMPORT_ERROR = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RANDOM_STATE = 42

# Maximum number of rows used to train the models.
MODEL_SAMPLE_SIZE = 30_000

# HDBSCAN uses a smaller representative sample.
HDBSCAN_SAMPLE_SIZE = 15_000

# Autoencoder batch size.
BATCH_SIZE = 1024

# Number of training epochs.
AUTOENCODER_EPOCHS = 8


# ---------------------------------------------------------------------------
# Feature preparation
# ---------------------------------------------------------------------------

def _feature_columns(df: pd.DataFrame) -> list[str]:
    """Return numeric features used by the anomaly models."""

    candidates = [
        "message_length",
        "word_count",
        "severity_score",
        "hour",
        "minute",
        "second",
    ]

    numeric = [
        column
        for column in candidates
        if column in df.columns
    ]

    # Include extracted numeric metrics where available.
    metric_cols = [
        column
        for column in df.columns
        if (
            column.startswith("metric_")
            and pd.api.types.is_numeric_dtype(df[column])
        )
    ]

    # Avoid making the feature space unnecessarily large.
    numeric.extend(metric_cols[:8])

    return numeric


def _make_matrix(
    df: pd.DataFrame,
    columns: list[str],
) -> np.ndarray:
    """Create a clean numeric feature matrix."""

    X = (
        df[columns]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )

    X = (
        X
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )

    return X.to_numpy(dtype=np.float32)


# ---------------------------------------------------------------------------
# Score utilities
# ---------------------------------------------------------------------------

def _percentile_flag(
    score: np.ndarray,
    percentile: float = 98.5,
) -> tuple[np.ndarray, float]:
    """Mark the highest scoring records as anomalies."""

    threshold = float(
        np.quantile(
            score,
            percentile / 100.0,
        )
    )

    return score >= threshold, threshold


def _minmax_percentile_score(
    score: np.ndarray,
) -> np.ndarray:
    """Convert arbitrary anomaly scores to a stable 0-1 percentile score."""

    ranks = (
        pd.Series(score)
        .rank(method="average", pct=True)
        .to_numpy(dtype=float)
    )

    return np.clip(ranks, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Autoencoder
# ---------------------------------------------------------------------------

if nn is not None:

    class _LogAutoencoder(nn.Module):
        """Small feed-forward autoencoder for operational log features."""

        def __init__(self, input_dim: int) -> None:
            super().__init__()

            hidden = max(
                16,
                min(
                    64,
                    input_dim * 4,
                ),
            )

            latent = max(
                8,
                min(
                    32,
                    input_dim * 2,
                ),
            )

            self.net = nn.Sequential(
                nn.Linear(
                    input_dim,
                    hidden,
                ),
                nn.ReLU(),

                nn.Linear(
                    hidden,
                    latent,
                ),
                nn.ReLU(),

                nn.Linear(
                    latent,
                    hidden,
                ),
                nn.ReLU(),

                nn.Linear(
                    hidden,
                    input_dim,
                ),
            )

        def forward(self, x):
            return self.net(x)


# ---------------------------------------------------------------------------
# Autoencoder scoring
# ---------------------------------------------------------------------------

def _autoencoder_scores(
    X: np.ndarray,
    sample_idx: np.ndarray,
) -> np.ndarray:
    """Train the autoencoder and return reconstruction error for every row."""

    if torch is None:

        detail = (
            f" Original import error: {TORCH_IMPORT_ERROR}"
            if TORCH_IMPORT_ERROR
            else ""
        )

        raise RuntimeError(
            "PyTorch could not be imported, so the Autoencoder cannot run."
            + detail
            + " Install/repair PyTorch in the active virtual environment "
              "with `python -m pip install --upgrade pip` followed by "
              "`python -m pip install --upgrade torch`, then restart "
              "Streamlit."
        )

    # Reproducibility.
    torch.manual_seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)

    # Use GPU when available.
    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    # Training subset.
    train_x = torch.tensor(
        X[sample_idx],
        dtype=torch.float32,
    )

    dataset = TensorDataset(train_x)

    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
    )

    # Build model.
    model = _LogAutoencoder(
        X.shape[1]
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=1e-3,
        weight_decay=1e-5,
    )

    loss_fn = nn.MSELoss()

    # -----------------------------------------------------------------------
    # Training
    # -----------------------------------------------------------------------

    model.train()

    for _ in range(AUTOENCODER_EPOCHS):

        for (batch,) in loader:

            batch = batch.to(device)

            optimizer.zero_grad(
                set_to_none=True
            )

            reconstructed = model(batch)

            loss = loss_fn(
                reconstructed,
                batch,
            )

            loss.backward()

            optimizer.step()

    # -----------------------------------------------------------------------
    # Calculate reconstruction error for the full dataset
    # -----------------------------------------------------------------------

    model.eval()

    scores = np.empty(
        len(X),
        dtype=np.float32,
    )

    with torch.no_grad():

        for start in range(
            0,
            len(X),
            BATCH_SIZE,
        ):

            end = min(
                start + BATCH_SIZE,
                len(X),
            )

            batch = torch.tensor(
                X[start:end],
                dtype=torch.float32,
                device=device,
            )

            reconstructed = model(batch)

            error = torch.mean(
                (
                    reconstructed - batch
                ) ** 2,
                dim=1,
            )

            scores[start:end] = (
                error
                .detach()
                .cpu()
                .numpy()
            )

    return scores.astype(float)


# ---------------------------------------------------------------------------
# HDBSCAN
# ---------------------------------------------------------------------------

def _hdbscan_scores(
    X: np.ndarray,
    sample_idx: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Run HDBSCAN on a representative sample.

    HDBSCAN is fitted on a representative sample instead of the entire
    dataset to keep the 253k-log dashboard responsive.

    PCA reduces the feature space before density clustering.

    The discovered cluster centroids are then used to calculate a
    full-dataset density-distance score.

    The UI should describe this as an HDBSCAN-based density score rather
    than an exact full-dataset HDBSCAN score.
    """

    # -----------------------------------------------------------------------
    # PCA
    # -----------------------------------------------------------------------

    pca_dim = min(
        8,
        X.shape[1],
        len(sample_idx),
    )

    reducer = PCA(
        n_components=pca_dim,
        random_state=RANDOM_STATE,
    )

    sample_x = reducer.fit_transform(
        X[sample_idx]
    )

    all_x = reducer.transform(X)

    # -----------------------------------------------------------------------
    # HDBSCAN
    # -----------------------------------------------------------------------

    model = HDBSCAN(
        min_cluster_size=50,
        min_samples=10,
        cluster_selection_method="eom",
        n_jobs=-1,
        copy=True,
    )

    sample_labels = model.fit_predict(
        sample_x
    )

    # Valid clusters.
    valid_labels = sorted(
        int(x)
        for x in np.unique(sample_labels)
        if x >= 0
    )

    scores = np.ones(
        len(X),
        dtype=float,
    )

    labels_all = np.full(
        len(X),
        -1,
        dtype=int,
    )

    # -----------------------------------------------------------------------
    # Cluster-centroid distance
    # -----------------------------------------------------------------------

    if valid_labels:

        centroids = np.vstack(
            [
                sample_x[
                    sample_labels == label
                ].mean(axis=0)

                for label in valid_labels
            ]
        )

        centroid_labels = np.asarray(
            valid_labels,
            dtype=int,
        )

        # Chunked nearest-centroid calculation.
        distances = np.empty(
            len(X),
            dtype=float,
        )

        nearest = np.empty(
            len(X),
            dtype=int,
        )

        for start in range(
            0,
            len(X),
            10_000,
        ):

            end = min(
                start + 10_000,
                len(X),
            )

            chunk = all_x[start:end]

            d2 = (
                (
                    chunk[:, None, :]
                    - centroids[None, :, :]
                ) ** 2
            ).sum(axis=2)

            idx = np.argmin(
                d2,
                axis=1,
            )

            distances[start:end] = np.sqrt(
                d2[
                    np.arange(len(chunk)),
                    idx,
                ]
            )

            nearest[start:end] = idx

        labels_all = centroid_labels[
            nearest
        ]

        scores = distances

        # -------------------------------------------------------------------
        # Determine anomaly threshold using HDBSCAN sample noise rate.
        # -------------------------------------------------------------------

        sample_distances = scores[
            sample_idx
        ]

        noise_rate = float(
            np.mean(
                sample_labels == -1
            )
        )

        percentile = max(
            98.5,
            100.0 * (
                1.0 - noise_rate
            ),
        )

        _, threshold = _percentile_flag(
            scores,
            percentile,
        )

        is_anomaly = (
            scores >= threshold
        )

    else:

        is_anomaly, threshold = (
            _percentile_flag(
                scores,
                98.5,
            )
        )

    # -----------------------------------------------------------------------
    # Silhouette score
    # -----------------------------------------------------------------------

    silhouette = np.nan

    cluster_mask = (
        sample_labels >= 0
    )

    if (
        cluster_mask.sum() >= 20
        and len(
            np.unique(
                sample_labels[
                    cluster_mask
                ]
            )
        ) >= 2
    ):

        sil_x = sample_x[
            cluster_mask
        ]

        sil_labels = sample_labels[
            cluster_mask
        ]

        # Keep silhouette calculation manageable.
        if len(sil_x) > 5_000:

            rng = np.random.default_rng(
                RANDOM_STATE
            )

            idx = rng.choice(
                len(sil_x),
                size=5_000,
                replace=False,
            )

            sil_x = sil_x[idx]
            sil_labels = sil_labels[idx]

        silhouette = float(
            silhouette_score(
                sil_x,
                sil_labels,
            )
        )

    # -----------------------------------------------------------------------
    # Metadata
    # -----------------------------------------------------------------------

    meta = {
        "clusters": len(valid_labels),

        "sample_noise_rate": float(
            np.mean(
                sample_labels == -1
            )
        ),

        "threshold": float(
            threshold
        ),

        "silhouette_score": silhouette,
    }

    return (
        scores,
        is_anomaly,
        meta,
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _evaluation_table(
    out: pd.DataFrame,
) -> pd.DataFrame:
    """Build model comparison metrics."""

    rule_positive = (
        out["severity_score"] >= 2
    )

    rows = []

    model_specs = [
        (
            "Isolation Forest",
            "isolation_forest_anomaly",
            "isolation_forest_score",
        ),

        (
            "Autoencoder",
            "autoencoder_anomaly",
            "autoencoder_score",
        ),

        (
            "HDBSCAN",
            "hdbscan_anomaly",
            "hdbscan_score",
        ),

        (
            "Ensemble (2/3)",
            "ensemble_anomaly",
            "ensemble_score",
        ),
    ]

    for (
        name,
        flag_col,
        score_col,
    ) in model_specs:

        flags = out[
            flag_col
        ].astype(bool)

        alignment = (
            float(
                (
                    flags
                    & rule_positive
                ).sum()
                / rule_positive.sum()
                * 100
            )
            if rule_positive.sum()
            else np.nan
        )

        rows.append(
            {
                "Model": name,

                "Anomalies": int(
                    flags.sum()
                ),

                "Anomaly rate (%)": round(
                    float(
                        flags.mean()
                        * 100
                    ),
                    2,
                ),

                "Rule alignment (%)": (
                    round(
                        alignment,
                        2,
                    )
                    if np.isfinite(
                        alignment
                    )
                    else np.nan
                ),

                "Median score": round(
                    float(
                        out[
                            score_col
                        ].median()
                    ),
                    4,
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


# ---------------------------------------------------------------------------
# Main anomaly detection pipeline
# ---------------------------------------------------------------------------

def detect_anomalies(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Run all anomaly models.

    PRIMARY MODEL:
        Autoencoder

    SECONDARY MODELS:
        Isolation Forest
        HDBSCAN

    ENSEMBLE:
        2-of-3 consensus
    """

    out = df.copy()

    # -----------------------------------------------------------------------
    # Feature selection
    # -----------------------------------------------------------------------

    numeric = _feature_columns(
        out
    )

    if not numeric:
        raise ValueError(
            "No numeric anomaly features are available."
        )

    X_raw = _make_matrix(
        out,
        numeric,
    )

    # -----------------------------------------------------------------------
    # Standardization
    # -----------------------------------------------------------------------

    scaler = StandardScaler()

    X = scaler.fit_transform(
        X_raw
    ).astype(np.float32)

    # -----------------------------------------------------------------------
    # Representative training sample
    # -----------------------------------------------------------------------

    sample_size = min(
        MODEL_SAMPLE_SIZE,
        len(out),
    )

    rng = np.random.default_rng(
        RANDOM_STATE
    )

    sample_idx = rng.choice(
        len(out),
        size=sample_size,
        replace=False,
    )

    # =======================================================================
    # 1) ISOLATION FOREST
    # =======================================================================

    isolation = IsolationForest(
        n_estimators=150,
        contamination="auto",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    isolation.fit(
        X[sample_idx]
    )

    isolation_score = (
        -isolation.decision_function(
            X
        )
    )

    isolation_anomaly, isolation_threshold = (
        _percentile_flag(
            isolation_score
        )
    )

    out[
        "isolation_forest_score"
    ] = isolation_score

    out[
        "isolation_forest_anomaly"
    ] = isolation_anomaly

    # =======================================================================
    # 2) AUTOENCODER — PRIMARY MODEL
    # =======================================================================

    # IMPORTANT:
    # Calculate the Autoencoder score FIRST.
    # Only after that do we assign it to anomaly_score/is_anomaly.
    autoencoder_score = _autoencoder_scores(
        X,
        sample_idx,
    )

    autoencoder_anomaly, autoencoder_threshold = (
        _percentile_flag(
            autoencoder_score
        )
    )

    out[
        "autoencoder_score"
    ] = autoencoder_score

    out[
        "autoencoder_anomaly"
    ] = autoencoder_anomaly

    # -----------------------------------------------------------------------
    # Autoencoder becomes the PRIMARY anomaly signal.
    #
    # Overview uses:
    #     view["is_anomaly"]
    #
    # Therefore Overview now shows Autoencoder anomalies.
    #
    # Incident correlation also uses is_anomaly through is_signal below.
    # -----------------------------------------------------------------------

    out[
        "anomaly_score"
    ] = autoencoder_score

    out[
        "is_anomaly"
    ] = autoencoder_anomaly

    # =======================================================================
    # 3) HDBSCAN-BASED DENSITY ANOMALY
    # =======================================================================

    hdb_sample_size = min(
        HDBSCAN_SAMPLE_SIZE,
        len(out),
    )

    hdb_sample_idx = rng.choice(
        len(out),
        size=hdb_sample_size,
        replace=False,
    )

    (
        hdbscan_score,
        hdbscan_anomaly,
        hdbscan_meta,
    ) = _hdbscan_scores(
        X,
        hdb_sample_idx,
    )

    out[
        "hdbscan_score"
    ] = hdbscan_score

    out[
        "hdbscan_anomaly"
    ] = hdbscan_anomaly

    # =======================================================================
    # 4) ENSEMBLE — 2 OF 3 MODELS
    # =======================================================================

    votes = (
        out[
            "isolation_forest_anomaly"
        ].astype(int)

        + out[
            "autoencoder_anomaly"
        ].astype(int)

        + out[
            "hdbscan_anomaly"
        ].astype(int)
    )

    out[
        "anomaly_votes"
    ] = votes

    out[
        "ensemble_anomaly"
    ] = votes >= 2

    # =======================================================================
    # NORMALIZED MODEL SCORES
    # =======================================================================

    out[
        "isolation_forest_percentile"
    ] = _minmax_percentile_score(
        isolation_score
    )

    out[
        "autoencoder_percentile"
    ] = _minmax_percentile_score(
        autoencoder_score
    )

    out[
        "hdbscan_percentile"
    ] = _minmax_percentile_score(
        hdbscan_score
    )

    # Average normalized score.
    out[
        "ensemble_score"
    ] = (
        out[
            "isolation_forest_percentile"
        ]

        + out[
            "autoencoder_percentile"
        ]

        + out[
            "hdbscan_percentile"
        ]
    ) / 3.0

    # =======================================================================
    # INCIDENT SIGNAL
    # =======================================================================

    # Because is_anomaly is now Autoencoder-based,
    # incident correlation also uses Autoencoder anomalies.
    #
    # Severity-based operational signals are still retained.
    out[
        "is_signal"
    ] = (
        out["is_anomaly"]
        | (
            out["severity_score"]
            >= 2
        )
    )

    # =======================================================================
    # EVALUATION METADATA
    # =======================================================================

    out.attrs[
        "anomaly_evaluation"
    ] = (
        _evaluation_table(
            out
        ).to_dict(
            "records"
        )
    )

    out.attrs[
        "anomaly_model_meta"
    ] = {
        "primary_model": "Autoencoder",

        "feature_count": len(
            numeric
        ),

        "features": numeric,

        "training_sample": sample_size,

        "hdbscan_sample": hdb_sample_size,

        "isolation_forest_threshold": (
            isolation_threshold
        ),

        "autoencoder_threshold": (
            autoencoder_threshold
        ),

        **hdbscan_meta,

        "ensemble_rule": (
            "2 of 3 models"
        ),
    }

    return out


# ---------------------------------------------------------------------------
# Public helper functions
# ---------------------------------------------------------------------------

def get_evaluation_metrics(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Return model comparison metrics generated during detection."""

    records = df.attrs.get(
        "anomaly_evaluation",
        [],
    )

    return pd.DataFrame(
        records
    )


def get_model_metadata(
    df: pd.DataFrame,
) -> dict:
    """Return anomaly model metadata."""

    return dict(
        df.attrs.get(
            "anomaly_model_meta",
            {},
        )
    )