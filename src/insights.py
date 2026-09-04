import os
import json
import pandas as pd

def _fallback_summary(incident, evidence):
    top_types = evidence["parsed_message_type"].value_counts().head(5).to_dict()
    top_components = evidence["component"].value_counts().head(5).to_dict()
    anomaly_count = int(evidence["is_anomaly"].sum())
    high_medium = int((evidence["severity_score"] >= 2).sum())

    return f"""
### Incident Summary

**{incident['incident_id']}** is a **{incident['severity']}** incident affecting
**{incident['primary_component']}** from **{incident['start_time']}** to
**{incident['end_time']}**.

- Evidence records: **{len(evidence)}**
- Anomalous records: **{anomaly_count}**
- Error/failure signals: **{high_medium}**
- Dominant components: `{top_components}`
- Dominant message types: `{top_types}`

**Assessment:** The incident is correlated from timestamp proximity and operational
error/anomaly signals. This is an evidence summary, not a definitive root-cause claim.
Review the evidence records before taking action.
""".strip()

def generate_ai_summary(incident, evidence):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"ok": False, "text": _fallback_summary(incident, evidence)}

    try:
        from litellm import completion

        rows = evidence[[
            "normalized_timestamp", "component",
            "parsed_message_type", "message",
            "severity", "is_anomaly"
        ]].copy()
        rows["normalized_timestamp"] = rows["normalized_timestamp"].astype(str)

        prompt = f"""
You are an SRE/log-analysis assistant.
Analyze ONLY the evidence below.

Incident metadata:
{json.dumps({
    "incident_id": incident["incident_id"],
    "severity": incident["severity"],
    "primary_component": incident["primary_component"],
    "start_time": str(incident["start_time"]),
    "end_time": str(incident["end_time"]),
    "event_count": int(incident["event_count"])
}, indent=2)}

Evidence:
{rows.to_json(orient="records", indent=2)}

Return:
1. Executive summary
2. Strongest evidence
3. Probable cause hypotheses, clearly labeled as hypotheses
4. Affected components
5. Recommended investigation steps
6. Confidence and limitations

Do not invent log events, metrics, root causes, or remediation results.
"""
        response = completion(
            model=os.getenv("GEMINI_MODEL", "gemini/gemini-3.6-flash"),
            messages=[
                {"role": "system", "content": "You are a precise, evidence-grounded log analyst."},
                {"role": "user", "content": prompt},
            ],
            api_key=api_key,
        )
        text = response.choices[0].message.content
        return {"ok": True, "text": text}
    except Exception as exc:
        return {"ok": False, "text": f"LLM analysis unavailable: {exc}\n\n{_fallback_summary(incident, evidence)}"}
