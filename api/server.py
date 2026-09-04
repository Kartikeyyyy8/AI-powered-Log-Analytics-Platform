import os
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()
from src.loader import load_logs
from src.features import build_features
from src.anomaly import detect_anomalies
from src.incidents import build_incidents

app = Flask(__name__)
DATA_PATH = os.getenv("LOG_FILE", "data/processed_logs.jsonl")

def analytics():
    df = load_logs(DATA_PATH)
    df = build_features(df)
    df = detect_anomalies(df)
    incidents = build_incidents(df)
    return df, incidents

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "logsense-api"})

@app.get("/api/summary")
def summary():
    df, incidents = analytics()
    return jsonify({
        "total_logs": len(df),
        "anomalies": int(df["is_anomaly"].sum()),
        "signals": int(df["is_signal"].sum()),
        "incidents": len(incidents),
        "components": int(df["component"].nunique()),
    })

@app.get("/api/incidents")
def get_incidents():
    _, incidents = analytics()
    records = incidents.copy()
    for col in ["start_time", "end_time"]:
        if col in records:
            records[col] = records[col].astype(str)
    return jsonify(records.to_dict(orient="records"))

@app.get("/api/logs")
def get_logs():
    df, _ = analytics()
    limit = min(max(int(request.args.get("limit", 100)), 1), 1000)
    records = df.head(limit).copy()
    records["normalized_timestamp"] = records["normalized_timestamp"].astype(str)
    return jsonify(records[[
        "event_id", "normalized_timestamp", "component",
        "parsed_message_type", "message", "severity",
        "anomaly_score", "is_anomaly"
    ]].to_dict(orient="records"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
