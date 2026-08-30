"""Profile raw log datasets before building the processing pipeline.

The profiler uses the shared LogNormalizer for timestamp normalization
guaranteeing a single source of truth across profiling and pipeline execution.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from LogProcessing.normalization.normalizer import LogNormalizer, ParsedTimestamp

CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")


def _decode_line(raw_line: bytes) -> str:
    return raw_line.decode("utf-8", errors="replace").rstrip("\r\n")


def _line_ending(raw_line: bytes) -> str:
    if raw_line.endswith(b"\r\n"):
        return "CRLF"
    if raw_line.endswith(b"\n"):
        return "LF"
    if raw_line.endswith(b"\r"):
        return "CR"
    return "NONE"


def _parse_healthapp_timestamp(value: str) -> ParsedTimestamp:
    return LogNormalizer.parse_timestamp(value)


def _message_type(message: str) -> str:
    stripped = message.strip()
    if not stripped:
        return "EMPTY_MESSAGE"

    if "REPORT :" in stripped:
        return "REPORT"
    if "SCREEN_ON" in stripped:
        return "SCREEN_ON"
    if "SCREEN_OFF" in stripped:
        return "SCREEN_OFF"
    if "TIME_TICK" in stripped:
        return "TIME_TICK"
    if "BOOT_COMPLETED" in stripped:
        return "BOOT_COMPLETED"
    if "FAILED_ERROR_DATA" in stripped:
        return "FAILED_ERROR_DATA"

    prefix = re.split(r"[\s=:|(]", stripped, maxsplit=1)[0]
    return prefix or "UNKNOWN"


def _message_pattern(message: str) -> str:
    compact = " ".join(message.strip().split())
    normalized_numbers = NUMBER_PATTERN.sub("<num>", compact)
    return normalized_numbers[:160] if normalized_numbers else "EMPTY_MESSAGE"


def _top(counter: Counter[str], limit: int) -> list[dict[str, int | str]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def profile_dataset(input_path: str | Path, top_limit: int = 25) -> dict[str, Any]:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    if not path.is_file():
        raise ValueError(f"Dataset path is not a file: {path}")

    field_counts: Counter[str] = Counter()
    line_endings: Counter[str] = Counter()
    components: Counter[str] = Counter()
    process_ids: Counter[str] = Counter()
    message_types: Counter[str] = Counter()
    message_patterns: Counter[str] = Counter()
    timestamp_issues: Counter[str] = Counter()
    quality_flags: Counter[str] = Counter()

    total_lines = 0
    blank_lines = 0
    valid_format_records = 0
    extra_separator_records = 0
    too_few_field_records = 0
    null_byte_lines = 0
    control_character_lines = 0
    replacement_character_lines = 0
    records_with_quality_flags = 0
    parseable_timestamps = 0
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    first_normalized_timestamp: str | None = None
    last_normalized_timestamp: str | None = None
    sample_malformed_lines: list[dict[str, Any]] = []
    sample_quality_issue_lines: list[dict[str, Any]] = []

    with path.open("rb") as handle:
        for raw_line in handle:
            total_lines += 1
            line_quality_flags: list[str] = []
            line_endings[_line_ending(raw_line)] += 1

            if b"\x00" in raw_line:
                null_byte_lines += 1
                line_quality_flags.append("contains_null_byte")
                quality_flags["contains_null_byte"] += 1

            decoded = _decode_line(raw_line)
            if "\ufffd" in decoded:
                replacement_character_lines += 1
                line_quality_flags.append("decode_replacement_character")
                quality_flags["decode_replacement_character"] += 1

            cleaned_for_blank_check = decoded.replace("\x00", "").strip()
            if not cleaned_for_blank_check:
                blank_lines += 1
                line_quality_flags.append("blank_line")
                field_counts["0"] += 1
                quality_flags["blank_line"] += 1
                records_with_quality_flags += 1
                if len(sample_malformed_lines) < 10:
                    sample_malformed_lines.append(
                        {"line_number": total_lines, "reason": "blank_line", "raw": decoded[:200]}
                    )
                continue

            if CONTROL_CHARACTER_PATTERN.search(decoded):
                control_character_lines += 1
                line_quality_flags.append("contains_control_character")
                quality_flags["contains_control_character"] += 1

            parts = decoded.split("|", 3)
            pipe_count = decoded.count("|")
            apparent_field_count = pipe_count + 1
            field_counts[str(apparent_field_count)] += 1

            if len(parts) < 4:
                too_few_field_records += 1
                line_quality_flags.append("too_few_fields")
                quality_flags["too_few_fields"] += 1
                records_with_quality_flags += 1
                if len(sample_malformed_lines) < 10:
                    sample_malformed_lines.append(
                        {
                            "line_number": total_lines,
                            "reason": "too_few_fields",
                            "raw": decoded[:200],
                        }
                    )
                continue

            valid_format_records += 1
            if pipe_count > 3:
                extra_separator_records += 1
                line_quality_flags.append("message_contains_pipe_separator")
                quality_flags["message_contains_pipe_separator"] += 1

            timestamp, component, process_id, message = parts
            if not component.strip():
                line_quality_flags.append("missing_component")
                quality_flags["missing_component"] += 1
            if not process_id.strip():
                line_quality_flags.append("missing_process_id")
                quality_flags["missing_process_id"] += 1
            if not message.strip():
                line_quality_flags.append("missing_message")
                quality_flags["missing_message"] += 1

            parsed_timestamp = _parse_healthapp_timestamp(timestamp.strip())
            if parsed_timestamp.issue:
                timestamp_issues[parsed_timestamp.issue] += 1
                line_quality_flags.append("timestamp_parse_failed")
                quality_flags["timestamp_parse_failed"] += 1
            else:
                parseable_timestamps += 1
                if first_timestamp is None:
                    first_timestamp = parsed_timestamp.original
                    first_normalized_timestamp = parsed_timestamp.normalized
                last_timestamp = parsed_timestamp.original
                last_normalized_timestamp = parsed_timestamp.normalized

            components[component.strip() or "UNKNOWN"] += 1
            process_ids[process_id.strip() or "UNKNOWN"] += 1
            message_types[_message_type(message)] += 1
            message_patterns[_message_pattern(message)] += 1

            if line_quality_flags:
                records_with_quality_flags += 1
                if len(sample_quality_issue_lines) < 10:
                    sample_quality_issue_lines.append(
                        {
                            "line_number": total_lines,
                            "flags": line_quality_flags,
                            "raw": decoded[:200],
                        }
                    )

    file_size_bytes = path.stat().st_size

    return {
        "dataset": {
            "path": str(path),
            "file_name": path.name,
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
            "profiled_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        "record_counts": {
            "total_lines": total_lines,
            "valid_format_records": valid_format_records,
            "blank_lines": blank_lines,
            "too_few_field_records": too_few_field_records,
            "extra_separator_records": extra_separator_records,
            "null_byte_lines": null_byte_lines,
            "control_character_lines": control_character_lines,
            "replacement_character_lines": replacement_character_lines,
            "records_with_quality_flags": records_with_quality_flags,
            "clean_candidate_records": total_lines - records_with_quality_flags,
        },
        "format": {
            "expected_shape": "timestamp|component|process_id|message",
            "parser_note": "Split only the first three pipe separators; the message may contain pipes.",
            "field_count_distribution": dict(sorted(field_counts.items(), key=lambda item: int(item[0]))),
            "line_ending_distribution": dict(line_endings),
        },
        "timestamps": {
            "format": "YYYYMMDD-H:m:s:SSS or compact variants such as YYYYMD-H:m:s:S",
            "parseable_timestamps": parseable_timestamps,
            "timestamp_parse_failures": sum(timestamp_issues.values()),
            "timestamp_issue_counts": dict(timestamp_issues),
            "first_timestamp": first_timestamp,
            "first_normalized_timestamp": first_normalized_timestamp,
            "last_timestamp": last_timestamp,
            "last_normalized_timestamp": last_normalized_timestamp,
        },
        "top_components": _top(components, top_limit),
        "top_process_ids": _top(process_ids, top_limit),
        "top_message_types": _top(message_types, top_limit),
        "top_message_patterns": _top(message_patterns, top_limit),
        "quality_flags": dict(quality_flags.most_common()),
        "sample_malformed_lines": sample_malformed_lines,
        "sample_quality_issue_lines": sample_quality_issue_lines,
        "recommendations": [
            "Use streaming ingestion because the dataset is large enough to avoid full-file reads.",
            "Implement a dedicated HealthApp parser that splits each line with maxsplit=3.",
            "Route corrupted records (e.g. null bytes in structural fields) to dead-letter output.",
            "Normalize custom timestamp formats into ISO 8601 UTC with single-source-of-truth semantics.",
            "Generate message_type and extracted_metrics fields for ML anomaly detection.",
            "Preserve exact raw lines for all records and dead letters for auditing.",
        ],
    }


def write_profile(profile: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile a raw HealthApp log dataset.")
    parser.add_argument("input_path", help="Path to the raw log file.")
    parser.add_argument(
        "--output",
        default="outputs/dataset_profile.json",
        help="Where to write the dataset profile JSON.",
    )
    parser.add_argument("--top-limit", type=int, default=25, help="Number of top values to keep.")
    args = parser.parse_args()

    profile = profile_dataset(args.input_path, top_limit=args.top_limit)
    output_path = write_profile(profile, args.output)
    print(f"Wrote dataset profile to {output_path}")
    print(
        "Profiled {total} lines: {valid} valid-format, {flagged} with quality flags.".format(
            total=profile["record_counts"]["total_lines"],
            valid=profile["record_counts"]["valid_format_records"],
            flagged=profile["record_counts"]["records_with_quality_flags"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
