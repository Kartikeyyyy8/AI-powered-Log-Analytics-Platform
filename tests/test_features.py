import pandas as pd
from src.features import build_features

def test_error_is_medium():
    df = pd.DataFrame([{
        "event_id": "1",
        "normalized_timestamp": "2017-01-01T00:00:00Z",
        "component": "A",
        "message": "database error occurred",
        "parsed_message_type": "error",
        "extracted_metrics": {},
    }])
    result = build_features(df)
    assert result.iloc[0]["severity"] == "Medium"
    assert result.iloc[0]["severity_score"] == 2
