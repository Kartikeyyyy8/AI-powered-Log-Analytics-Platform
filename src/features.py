import re
import pandas as pd

HIGH_PATTERNS = [
    r"\bfatal\b", r"\bcrash(?:ed)?\b", r"\bpanic\b",
    r"\bexception\b", r"\btimeout\b", r"\bdenied\b",
]
MEDIUM_PATTERNS = [
    r"\berror\b", r"\bfail(?:ed|ure)?\b", r"\binvalid\b",
    r"\bunable\b", r"\bnot found\b",
]
LOW_PATTERNS = [r"\bwarn(?:ing)?\b"]

def _severity(message: str) -> tuple[str, int]:
    text = message.lower()
    if any(re.search(p, text) for p in HIGH_PATTERNS):
        return "High", 3
    if any(re.search(p, text) for p in MEDIUM_PATTERNS):
        return "Medium", 2
    if any(re.search(p, text) for p in LOW_PATTERNS):
        return "Low", 1
    return "Normal", 0

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    sev = out["message"].map(_severity)
    out["severity"] = sev.map(lambda x: x[0])
    out["severity_score"] = sev.map(lambda x: x[1])

    out["message_length"] = out["message"].str.len()
    out["word_count"] = out["message"].str.split().str.len()
    out["has_metric"] = out.get("extracted_metrics", pd.Series([{}] * len(out))).map(
        lambda x: bool(x) if isinstance(x, dict) else False
    )
    out["hour"] = out["normalized_timestamp"].dt.hour
    out["minute"] = out["normalized_timestamp"].dt.minute
    out["second"] = (
        out["normalized_timestamp"].dt.second
        + out["normalized_timestamp"].dt.microsecond / 1_000_000
    )

    # Numeric metrics extracted by the user's processing pipeline.
    metrics = out.get("extracted_metrics")
    if metrics is not None:
        metric_df = pd.json_normalize(metrics).add_prefix("metric_")
        metric_df.index = out.index
        out = pd.concat([out, metric_df], axis=1)

    return out
