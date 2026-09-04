import pandas as pd
from src.features import build_features
from src.anomaly import detect_anomalies
from src.incidents import build_incidents

def test_incident_generation():
    rows = []
    for i in range(20):
        rows.append({
            "event_id": str(i),
            "normalized_timestamp": f"2017-01-01T00:00:{i:02d}Z",
            "component": "A",
            "message": "save failed" if i in (5, 6, 7) else "normal event",
            "parsed_message_type": "x",
            "extracted_metrics": {},
        })
    df = build_features(pd.DataFrame(rows))
    # Ensure the incident builder is independently testable.
    df["is_anomaly"] = False
    df["is_signal"] = df["severity_score"] >= 2
    incidents = build_incidents(df)
    assert len(incidents) >= 1
