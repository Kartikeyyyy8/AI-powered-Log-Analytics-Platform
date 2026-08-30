# LogProcessing Module — AI-Powered Log Analytics Platform

## Overview

The `LogProcessing` module is the hardened, dataset-aware data pipeline for the AI-Powered Log Analytics Platform. It ingests raw, semi-structured system logs (specifically `HealthApp.log`), performs rigorous data quality and corruption checks, parses domain payloads, normalizes irregular timestamps into ISO 8601 UTC, extracts domain metrics, validates records against strict contracts, and outputs streamable, ML-ready JSON Lines (`.jsonl`) data.

Downstream consumers (such as **Member 2 — Anomaly Detection**) consume the processed records directly without needing to handle dataset quirks, separator nuances, or custom parsing.

---

## Dataset Characteristics & Semantics (`HealthApp.log`)

- **File size**: ~22.44 MB (23,529,930 bytes)
- **Total records**: 253,395 lines
- **Encoding**: ASCII (handled in UTF-8 binary mode)
- **Line terminators**: CRLF (`\r\n`)
- **Logical format**: `timestamp|component|process_id|message`

### Key Dataset Quirks & Policies:

1. **Extra Pipe Separators (`maxsplit=3`)**:
   - Messages frequently contain additional `|` characters (e.g. `tryToReloadTodayBasicSteps1514893168960|0|14696|0` or `upDateHealthNotification()|214|7.14|10000`).
   - **Policy**: The parser splits strictly on the first 3 pipe delimiters (`split("|", 3)`). These records are **valid** and tagged with the quality flag `"message_contains_pipe_separator"`.
2. **Compact & Irregular Timestamps**:
   - Dates can be 8 digits (`20171223` -> 2017-12-23) or 6 digits (`201812` -> 2018-01-02, `201813` -> 2018-01-03).
   - Time fields may omit leading zeros (`9:59:0:95`).
   - **Millisecond Semantics**: Non-padded milliseconds are values in `0..999`. For example, `:95` = 95ms (`.095Z`), `:11` = 11ms (`.011Z`), `:6` = 6ms (`.006Z`), and `:606` = 606ms (`.606Z`).
   - **Single Source of Truth**: Timestamp parsing is unified in `LogNormalizer.parse_timestamp` across both the dataset profiler and the runtime normalizer.
3. **Corrupted Records & Dead-Letter Handling**:
   - Records with raw byte-level corruption (e.g. Line 238724 with 106 leading `\x00` null bytes) or unparseable timestamps are **NOT** silently repaired into clean data.
   - **Policy**: Corrupted records are routed directly to `dead_letter_logs.jsonl` with their exact line number, full unmodified raw message, failure reason, and corruption flags preserved.

---

## Architecture & Pipeline Flow

```
HealthApp.log
      │
      ▼
[ 1. Streaming Ingestor ]       Line-by-line binary stream with batch run timestamp
      │
      ▼
[ 2. HealthApp Parser ]         maxsplit=3 pipe parser; flags corruption & extra pipes
      │
      ▼
[ 3. Log Cleaner ]              Safe whitespace normalization; retains corruption flags
      │
      ▼
[ 4. Log Normalizer ]           Single source of truth timestamp parser -> ISO 8601 UTC
      │
      ▼
[ 5. Message Classifier ]       Extracts semantic event types & numeric domain metrics
      │
      ▼
[ 6. Log Validator ]            Enforces required fields, types, and corruption rejection
      │
      ├── [ Valid: 253,394 ] ──► JsonLinesWriter ─────► processed_logs.jsonl
      │
      └── [ Invalid: 1 ] ──────► DeadLetterWriter ────► dead_letter_logs.jsonl
      │
      ▼
[ 7. Quality Analyzer ]         Reconciles metrics & counts ──► quality_report.json
```

---

## Canonical Schemas

### 1. Processed Log (`StructuredLogRecord` in `processed_logs.jsonl`)

Each line is a self-contained, validated JSON object:

```json
{
  "event_id": "healthapp_000001",
  "timestamp": "20171223-22:15:29:606",
  "normalized_timestamp": "2017-12-23T22:15:29.606Z",
  "ingestion_timestamp": "2026-08-30T16:12:49.808788Z",
  "component": "Step_LSC",
  "process_id": "30002312",
  "message": "onStandStepChanged 3579",
  "parsed_message_type": "onStandStepChanged",
  "extracted_metrics": {
    "step_count": 3579
  },
  "source": "HealthApp.log",
  "line_number": 1,
  "raw_message": "20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579",
  "quality_flags": [],
  "metadata": {
    "pipe_count": 3,
    "byte_size": 65,
    "line_ending": "CRLF"
  }
}
```

### 2. Dead-Letter Log (`DeadLetterLogRecord` in `dead_letter_logs.jsonl`)

```json
{
  "source": "HealthApp.log",
  "line_number": 238724,
  "raw_message": "\u0000\u0000...201812-19:39:28:633|Step_StaticReceiver|30002312|onReceive action: android.intent.action.BOOT_COMPLETED",
  "error_reason": "corrupted_record: input contains null bytes",
  "ingestion_timestamp": "2026-08-30T16:12:49.808788Z",
  "quality_flags": ["contains_null_byte", "contains_control_character", "cleaned_null_bytes", "validation_failed"],
  "metadata": {
    "validation_errors": ["corrupted_record: input contains null bytes"]
  }
}
```

---

## Integration Contract for Member 2 (Anomaly Detection)

Downstream ML / Anomaly Detection components should consume `LogProcessing/outputs/processed_logs.jsonl`.

Key features for anomaly modeling:
- `event_id`: Deterministic unique identifier (`healthapp_000001`).
- `normalized_timestamp`: Standard ISO 8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SS.mmmZ`) for time-series aggregation, windowing, and delta calculation.
- `component`: Categorical feature representing the Android subsystem (e.g. `Step_LSC`, `HiH_HiSyncControl`).
- `parsed_message_type`: Controlled event label (e.g. `onStandStepChanged`, `calculateCaloriesWithCache`, `SCREEN_ON`, `TIME_TICK`).
- `extracted_metrics`: Key-value pairs of numeric telemetry (`step_count`, `total_calories`, `total_altitude`, `timestamp_ms`).
- `quality_flags`: Clean metadata tags indicating non-fatal variations (e.g. `message_contains_pipe_separator`).

---

## How to Run

### Execute the Processing Pipeline

From the repository root:

```bash
python3 -m LogProcessing.services.pipeline /path/to/HealthApp.log --output-dir LogProcessing/outputs
```

Or via Python API:

```python
from LogProcessing import process_logs

result = process_logs(
    input_path="/path/to/HealthApp.log",
    output_dir="LogProcessing/outputs",
    generate_profile=True,
)

print(f"Processed {result.valid_records} valid records, {result.invalid_records} dead letter records.")
```

### Run Tests

```bash
python3 -m pytest LogProcessing/tests -v
```
