import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from src.loader import load_logs
from src.features import build_features
from src.anomaly import detect_anomalies, get_evaluation_metrics, get_model_metadata, TORCH_IMPORT_ERROR
from src.incidents import build_incidents
from src.insights import generate_ai_summary
from src.charts import (
    render_overview_charts, render_anomaly_chart, render_model_anomaly_chart,
    render_model_comparison_chart, render_consensus_chart, render_incident_timeline
)

st.set_page_config(
    page_title="LogSense — AI Log Analytics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background: #f7f9fc; }
    [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e5e7eb; }
    .block-container { max-width: 1450px; padding-top: 1.5rem; }
    .hero { background:#ffffff; border:1px solid #e5e7eb; border-radius:16px;
            padding:22px 26px; margin-bottom:18px; }
    .hero h1 { margin:0; color:#111827; font-size:2rem; }
    .hero p { color:#6b7280; margin:6px 0 0; }
    .metric-card { background:#fff; border:1px solid #e5e7eb; border-radius:14px;
                   padding:16px; }
    .metric-label { color:#6b7280; font-size:.82rem; }
    .metric-value { color:#111827; font-size:1.55rem; font-weight:700; }
    .sev-high { color:#b91c1c; font-weight:700; }
    .sev-medium { color:#b45309; font-weight:700; }
    .sev-low { color:#047857; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🛡️ LogSense — AI-Powered Log Analytics & Incident Intelligence</h1>
<p>Detect anomalies, correlate incidents, investigate evidence, and generate grounded operational insights.</p>
</div>
""", unsafe_allow_html=True)

DATA_PATH = st.sidebar.text_input(
    "Processed log file",
    value=os.getenv("LOG_FILE", "data/processed_logs.jsonl"),
)
if not os.path.exists(DATA_PATH):
    st.error(f"Dataset not found: {DATA_PATH}")
    st.info("Copy your processed_logs.jsonl into data/ or set LOG_FILE to its path.")
    st.stop()

@st.cache_data(show_spinner="Loading processed logs…")
def get_logs(path):
    return load_logs(path)

@st.cache_data(show_spinner="Building analytics features…")
def get_features(df):
    return build_features(df)

@st.cache_data(show_spinner="Running anomaly detection…")
def get_anomalies(df):
    return detect_anomalies(df)

@st.cache_data(show_spinner="Correlating incidents…")
def get_incidents(df):
    return build_incidents(df)

df = get_logs(DATA_PATH)
features = get_features(df)
try:
    analysis = get_anomalies(features)
except RuntimeError as exc:
    st.error("Anomaly detection could not start.")
    st.code(str(exc))
    if TORCH_IMPORT_ERROR is not None:
        st.warning(
            "The Autoencoder dependency (PyTorch) is not importable in the Python "
            "environment currently running Streamlit. Run the installation commands "
            "shown above in that same environment, then restart Streamlit."
        )
    st.stop()
incidents = get_incidents(analysis)

# `is_anomaly`, `anomaly_score`, and `is_signal` are created by the
# anomaly-detection stage, so all dashboard analytics must use `analysis`.
view = analysis.copy()

components = sorted(view["component"].dropna().unique().tolist())
types = sorted(view["parsed_message_type"].dropna().unique().tolist())

st.sidebar.markdown("### Filters")
selected_components = st.sidebar.multiselect("Component", components)
selected_types = st.sidebar.multiselect("Message type", types)
min_severity = st.sidebar.selectbox("Minimum severity", ["All", "Low", "Medium", "High"])

if selected_components:
    view = view[view["component"].isin(selected_components)]
if selected_types:
    view = view[view["parsed_message_type"].isin(selected_types)]
if min_severity != "All":
    order = {"Low": 1, "Medium": 2, "High": 3}
    view = view[view["severity_score"] >= order[min_severity]]

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview", "Log Explorer", "Anomalies", "Incidents", "AI Assistant"]
)

with tab1:
    total = len(view)
    anomaly_count = int(view["is_anomaly"].sum())
    incident_count = len(incidents)
    error_like = int((view["severity_score"] >= 2).sum())

    cols = st.columns(4)
    metrics = [
        ("Processed logs", f"{total:,}"),
        ("Anomalies", f"{anomaly_count:,}"),
        ("Error/Failure signals", f"{error_like:,}"),
        ("Correlated incidents", f"{incident_count:,}"),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.markdown(
            f'<div class="metric-card"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()
    render_overview_charts(view, incidents)

    st.subheader("Top affected components")
    comp = (
        view.groupby("component")
        .agg(logs=("event_id", "count"), anomalies=("is_anomaly", "sum"))
        .sort_values(["anomalies", "logs"], ascending=False)
        .head(12)
    )
    st.dataframe(comp, width="stretch")

with tab2:
    st.subheader("Log Explorer")
    search = st.text_input("Search message / raw message")
    limit = st.slider("Rows", 50, 1000, 200, step=50)

    explorer = view
    if search:
        mask = explorer["message"].str.contains(search, case=False, na=False)
        explorer = explorer[mask]

    cols = [
        "event_id", "normalized_timestamp", "component",
        "parsed_message_type", "message", "severity",
        "anomaly_score", "is_anomaly"
    ]
    st.dataframe(explorer[cols].head(limit), width="stretch", height=520)

with tab3:
    st.subheader("Anomaly Detection")
    st.caption(
        "Three complementary unsupervised detectors are compared: Isolation Forest, "
        "Autoencoder reconstruction error, and HDBSCAN-based density analysis. "
        "The existing Isolation Forest signal is retained for the rest of the platform; "
        "the 2-of-3 ensemble is shown here as a stronger consensus signal."
    )

    # --------------------------- Model overview ---------------------------
    model_cols = st.columns(4)
    model_cards = [
        ("Isolation Forest", int(analysis["isolation_forest_anomaly"].sum())),
        ("Autoencoder", int(analysis["autoencoder_anomaly"].sum())),
        ("HDBSCAN", int(analysis["hdbscan_anomaly"].sum())),
        ("2-of-3 Consensus", int(analysis["ensemble_anomaly"].sum())),
    ]
    for col, (label, value) in zip(model_cols, model_cards):
        col.metric(label, f"{value:,}")

    st.divider()

    # --------------------------- Model charts -----------------------------
    st.markdown("### 1. Isolation Forest")
    render_anomaly_chart(
        analysis,
        score_column="isolation_forest_score",
        title="Isolation Forest anomaly score over time",
    )

    st.markdown("### 2. Autoencoder")
    st.caption(
        "Higher reconstruction error means the log record is less similar to the "
        "patterns learned by the autoencoder."
    )
    render_model_anomaly_chart(
        analysis,
        score_column="autoencoder_score",
        flag_column="autoencoder_anomaly",
        title="Autoencoder reconstruction error over time",
    )

    st.markdown("### 3. HDBSCAN")
    st.caption(
        "HDBSCAN discovers dense behavioral groups on a representative sample; "
        "the full dataset is scored using distances to the discovered cluster centers "
        "to keep the 253k-log dashboard responsive."
    )
    render_model_anomaly_chart(
        analysis,
        score_column="hdbscan_score",
        flag_column="hdbscan_anomaly",
        title="HDBSCAN-based density anomaly score over time",
    )

    # --------------------------- Evaluation --------------------------------
    st.markdown("### Model evaluation & comparison")
    st.info(
        "Because this is an unlabeled anomaly-detection dataset, precision, recall, "
        "F1 and accuracy would not be scientifically valid. The dashboard therefore "
        "reports anomaly rate, alignment with existing error/failure rules, model "
        "consensus, and HDBSCAN clustering quality instead."
    )

    metrics = get_evaluation_metrics(analysis)
    st.dataframe(metrics, width="stretch", hide_index=True)

    left_eval, right_eval = st.columns(2)
    with left_eval:
        render_model_comparison_chart(metrics)
    with right_eval:
        render_consensus_chart(analysis)

    # Pairwise agreement is useful for understanding whether the models are
    # detecting the same behavior or complementary anomalies.
    st.markdown("#### Pairwise model agreement")
    pairwise = pd.DataFrame(
        {
            "Isolation Forest vs Autoencoder": [
                round(float((analysis["isolation_forest_anomaly"] == analysis["autoencoder_anomaly"]).mean() * 100), 2)
            ],
            "Isolation Forest vs HDBSCAN": [
                round(float((analysis["isolation_forest_anomaly"] == analysis["hdbscan_anomaly"]).mean() * 100), 2)
            ],
            "Autoencoder vs HDBSCAN": [
                round(float((analysis["autoencoder_anomaly"] == analysis["hdbscan_anomaly"]).mean() * 100), 2)
            ],
        }
    )
    pairwise = pairwise.rename(index={0: "Agreement (%)"})
    st.dataframe(pairwise, width="stretch")

    meta = get_model_metadata(analysis)
    with st.expander("Model configuration"):
        st.json(meta)

    st.divider()
    st.markdown("### Anomaly records")
    anomaly_view = analysis[analysis["ensemble_anomaly"]].copy()
    st.write(f"Detected **{len(anomaly_view):,}** high-confidence anomalous records by 2-of-3 model consensus.")
    cols = [
        "event_id", "normalized_timestamp", "component",
        "parsed_message_type", "message", "anomaly_votes",
        "ensemble_score", "isolation_forest_score",
        "autoencoder_score", "hdbscan_score", "severity"
    ]
    st.dataframe(
        anomaly_view.sort_values("ensemble_score", ascending=False)[cols].head(500),
        width="stretch",
        height=520,
    )

with tab4:
    st.subheader("Incident Intelligence")
    render_incident_timeline(incidents)

    if incidents.empty:
        st.success("No correlated incidents detected under the current rules.")
    else:
        st.dataframe(incidents, width="stretch", height=520)

with tab5:
    st.subheader("AI Incident Assistant")
    if incidents.empty:
        st.info("No incidents are currently available for AI investigation.")
    else:
        incident_ids = incidents["incident_id"].tolist()
        selected_id = st.selectbox("Incident", incident_ids)
        incident = incidents[incidents["incident_id"] == selected_id].iloc[0]

        st.write({
            "Incident": incident["incident_id"],
            "Severity": incident["severity"],
            "Component": incident["primary_component"],
            "Start": incident["start_time"],
            "End": incident["end_time"],
            "Events": int(incident["event_count"]),
        })

        evidence = analysis[
            (analysis["normalized_timestamp"] >= incident["start_time"]) &
            (analysis["normalized_timestamp"] <= incident["end_time"])
        ].sort_values("normalized_timestamp").head(40)

        with st.expander("Evidence used by the assistant", expanded=True):
            st.dataframe(
                evidence[[
                    "normalized_timestamp", "component",
                    "parsed_message_type", "message",
                    "severity", "is_anomaly"
                ]],
                width="stretch",
            )

        if st.button("Generate grounded incident summary", type="primary"):
            with st.spinner("Analyzing evidence…"):
                result = generate_ai_summary(incident, evidence)
            if result["ok"]:
                st.markdown(result["text"])
            else:
                st.warning(result["text"])
                st.caption("Set GEMINI_API_KEY to enable the LLM summary.")

st.caption(
    "AI-powered log analytics for anomaly detection, incident correlation, and intelligent operational insights."
)
