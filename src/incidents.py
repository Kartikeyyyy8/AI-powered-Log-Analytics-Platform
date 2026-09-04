import pandas as pd

def build_incidents(df: pd.DataFrame, gap_minutes: int = 5) -> pd.DataFrame:
    signals = df[df["is_signal"]].copy()
    if signals.empty:
        return pd.DataFrame(columns=[
            "incident_id", "start_time", "end_time", "duration_minutes",
            "event_count", "affected_components", "primary_component",
            "severity", "anomaly_count"
        ])

    signals = signals.sort_values("normalized_timestamp")
    time_gap = signals["normalized_timestamp"].diff().dt.total_seconds().div(60)
    component_change = signals["component"].ne(signals["component"].shift())
    new_group = ((time_gap > gap_minutes) | (component_change & (time_gap > 1))).fillna(True)
    signals["incident_group"] = new_group.cumsum()

    records = []
    for gid, group in signals.groupby("incident_group"):
        start = group["normalized_timestamp"].min()
        end = group["normalized_timestamp"].max()
        sev_score = int(group["severity_score"].max())
        severity = {3: "High", 2: "Medium", 1: "Low", 0: "Low"}[sev_score]
        primary = group["component"].value_counts().idxmax()

        records.append({
            "incident_id": f"INC-{int(gid):05d}",
            "start_time": start,
            "end_time": end,
            "duration_minutes": round((end - start).total_seconds() / 60, 2),
            "event_count": len(group),
            "affected_components": ", ".join(group["component"].value_counts().head(8).index),
            "primary_component": primary,
            "severity": severity,
            "anomaly_count": int(group["is_anomaly"].sum()),
        })

    result = pd.DataFrame(records)
    if not result.empty:
        result = result.sort_values(
            ["severity", "start_time"],
            ascending=[True, False]
        ).reset_index(drop=True)
    return result
