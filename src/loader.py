import json
from pathlib import Path
import pandas as pd

def load_logs(path: str) -> pd.DataFrame:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("The processed log file contains no records.")

    required = [
        "event_id", "normalized_timestamp", "component",
        "message", "parsed_message_type"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["normalized_timestamp"] = pd.to_datetime(
        df["normalized_timestamp"], errors="coerce", utc=True
    )
    df["message"] = df["message"].fillna("").astype(str)
    df["component"] = df["component"].fillna("unknown").astype(str)
    df["parsed_message_type"] = (
        df["parsed_message_type"].fillna("unknown").astype(str)
    )
    return df.sort_values("normalized_timestamp").reset_index(drop=True)
