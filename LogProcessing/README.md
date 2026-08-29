# LogProcessing Module — AI-Powered Log Analytics Platform

## Overview

The `LogProcessing` module is the dataset-aware data pipeline for the AI-Powered Log Analytics Platform. It ingests raw, semi-structured system logs (specifically `HealthApp.log`), performs data quality checks, cleans control/null bytes, parses domain payloads, normalizes irregular timestamps into ISO 8601 UTC, extracts domain metrics, validates records against strict data contracts, and outputs streamable, ML-ready JSON Lines (`.jsonl`) data.

Downstream consumers (such as **Member 2 — Anomaly Detection**) consume the processed records directly without needing to handle dataset quirks or implement custom parsing.

---

## Dataset Characteristics (`HealthApp.log`)

- **File size**: ~22.44 MB (23,529,930 bytes)
- **Total records**: 253,395 lines
- **Encoding**: ASCII (handled in UTF-8 binary mode)
- **Line terminators**: CRLF (`\r\n`)
- **Logical format**: `timestamp|component|process_id|message`
- **Known quirks handled**:
  - **Extra pipe characters**: Messages may contain additional `|` separators (e.g. `tryToReloadTodayBasicSteps1514893168960|0|14696|0`). Parsed strictly via `maxsplit=3`.
  - **Compact timestamps**: Dates can be 8 digits (`20171223`) or 6 digits (`201812` -> 2018-01-02), and time components may omit leading zeros (`9:59:0:95`).
  - **Corrupted lines & Null bytes**: Corrupted lines (e.g. line 238724 with prepended `\x00` null bytes) are detected, cleaned, preserved in raw audit fields, and tagged with quality flags.

---

## Architecture & Pipeline Flow

```
HealthApp.log
      │
      ▼
[ 1. Streaming Ingestor ]       Line-by-line streaming, binary mode, memory efficient
      │
      ▼
[ 2. HealthApp Parser ]         maxsplit=3 pipe parser; separates envelope from message
      │
      ▼
[ 3. Log Cleaner ]              Strips null bytes & control chars; preserves raw message
      │
      ▼
[ 4. Log Normalizer ]           Parses compact timestamps -> ISO 8601 UTC; generates stable event_id
      │
      ▼
[ 5. Message Classifier ]       Extracts semantic event type & numeric domain metrics
      │
      ▼
[ 6. Log Validator ]            Validates required fields, positive line numbers, clean metrics
      │
      ├── [ Valid ] ──────────► JsonLinesWriter ─────► processed_logs.jsonl
      │
      └── [ Invalid ] ────────► DeadLetterWriter ────► dead_letter_logs.jsonl
      │
      ▼
[ 7. Quality Analyzer ]         Aggregates distributions & metrics ──► quality_report.json
```

---

## Directory Structure

```
LogProcessing/
├── README.md                           # Comprehensive documentation
├── __init__.py                         # Public API exports
│
├── config/                             # Pipeline configuration
│   ├── __init__.py
│   └── settings.py
│
├── ingestion/                          # Streaming file reader
│   ├── __init__.py
│   ├── base.py                         # Abstract BaseIngestor
│   └── file_ingestor.py                # Line-by-line binary ingestor
│
├── parsing/                            # Log & message parsing
│   ├── __init__.py
│   ├── base.py                         # BaseParser & ParsedLogRecord
│   ├── healthapp_parser.py             # Dedicated 3-split pipe parser
│   └── message_classifier.py          # Event classifier & metric extractor
│
├── cleaning/                           # Data-aware text cleaning
│   ├── __init__.py
│   └── cleaner.py                      # Control character & null byte cleaner
│
├── normalization/                      # Format normalization
│   ├── __init__.py
│   └── normalizer.py                   # ISO timestamp & deterministic event ID
│
├── validation/                         # Data contract validation
│   ├── __init__.py
│   ├── rules.py                        # Modular rule functions
│   └── validator.py                    # Multi-rule validator
│
├── quality/                            # Data quality analysis
│   ├── __init__.py
│   ├── metrics.py                      # Metrics accumulator
│   └── analyzer.py                     # Report compiler
│
├── storage/                            # Streaming output writers
│   ├── __init__.py
│   ├── writer.py                       # JSONL & JSON report writers
│   └── dead_letter.py                  # Dead-letter queue writer
│
├── schemas/                            # Data contracts
│   ├── __init__.py
│   ├── raw_log.py                      # RawLogRecord
│   ├── structured_log.py               # Canonical StructuredLogRecord
│   ├── dead_letter_log.py              # DeadLetterLogRecord
│   └── quality_report.py               # QualityReport
│
├── profiling/                          # Phase 1 dataset profiler
│   ├── __init__.py
│   └── dataset_profiler.py
│
├── services/                           # Orchestration service
│   ├── __init__.py
│   └── pipeline.py                     # process_logs() entrypoint & CLI
│
├── outputs/                            # Default output artifacts
│   ├── processed_logs.jsonl
│   ├── dead_letter_logs.jsonl
│   ├── quality_report.json
│   └── dataset_profile.json
│
└── tests/                              # Comprehensive test suite (37 tests)
    ├── test_cleaning.py
    ├── test_dataset_profiler.py
    ├── test_file_ingestor.py
    ├── test_healthapp_parser.py
    ├── test_message_classifier.py
    ├── test_normalization.py
    ├── test_pipeline.py
    ├── test_quality.py
    ├── test_storage.py
    └── test_validation.py
```

---

## Canonical Schemas

### 1. Processed Log (`StructuredLogRecord` in `processed_logs.jsonl`)

Each line is a self-contained JSON object:

```json
{
  "event_id": "healthapp_000001",
  "timestamp": "20171223-22:15:29:606",
  "normalized_timestamp": "2017-12-23T22:15:29.606Z",
  "ingestion_timestamp": "2026-08-29T10:30:00Z",
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
    "byte_size": 60,
    "line_ending": "CRLF"
  }
}
```

### 2. Dead-Letter Log (`DeadLetterLogRecord` in `dead_letter_logs.jsonl`)

```json
{
  "source": "HealthApp.log",
  "line_number": 150,
  "raw_message": "corrupted line content",
  "error_reason": "parsing_failed: Line 150 has 2 fields, expected 4",
  "ingestion_timestamp": "2026-08-29T10:30:00Z",
  "quality_flags": ["parsing_failed"],
  "metadata": {
    "exception_type": "MalformedRecordError"
  }
}
```

---

## Integration Contract for Member 2 (Anomaly Detection)

Downstream ML / Anomaly Detection components should consume `LogProcessing/outputs/processed_logs.jsonl`.

Key fields for ML features:
- `event_id`: Deterministic unique identifier (`healthapp_000001`).
- `normalized_timestamp`: Standard ISO 8601 UTC timestamp for time-series aggregation and windowing.
- `component`: Categorical feature representing the subsystem (e.g. `Step_LSC`, `HiH_HiSyncControl`).
- `parsed_message_type`: Controlled event label (e.g. `onStandStepChanged`, `calculateCaloriesWithCache`, `SCREEN_ON`, `TIME_TICK`).
- `extracted_metrics`: Key-value pairs of numeric telemetry (`step_count`, `total_calories`, `total_altitude`, `timestamp_ms`).
- `quality_flags`: List of anomaly/quality indicators (e.g. `contains_null_byte`, `message_contains_pipe_separator`).

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

print(f"Processed {result.valid_records} valid records out of {result.total_records} total lines.")
```

### Run Tests

```bash
python3 -m pytest LogProcessing/tests -v
```
