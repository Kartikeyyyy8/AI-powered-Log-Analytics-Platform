"""Validation rules for structured log records."""

from __future__ import annotations

import re
from typing import Any

from LogProcessing.schemas.structured_log import StructuredLogRecord

CONTROL_CHAR_CHECK_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def check_required_fields(record: StructuredLogRecord) -> list[str]:
    """Check that all required fields are present and non-empty."""
    errors: list[str] = []
    if not record.timestamp or not str(record.timestamp).strip():
        errors.append("missing_required_field: timestamp")
    if not record.component or not str(record.component).strip():
        errors.append("missing_required_field: component")
    if not record.process_id or not str(record.process_id).strip():
        errors.append("missing_required_field: process_id")
    if not record.message or not str(record.message).strip():
        errors.append("missing_required_field: message")
    if not record.source or not str(record.source).strip():
        errors.append("missing_required_field: source")
    if not record.ingestion_timestamp or not str(record.ingestion_timestamp).strip():
        errors.append("missing_required_field: ingestion_timestamp")
    return errors


def check_line_number(record: StructuredLogRecord) -> list[str]:
    """Ensure line number is positive."""
    if record.line_number <= 0:
        return [f"invalid_line_number: {record.line_number} (must be > 0)"]
    return []


def check_extracted_metrics(record: StructuredLogRecord) -> list[str]:
    """Ensure extracted metrics contain valid numeric or string values."""
    errors: list[str] = []
    for metric_name, value in record.extracted_metrics.items():
        if value is None:
            continue
        if not isinstance(value, (int, float, str, bool)):
            errors.append(f"invalid_metric_type: {metric_name} is {type(value).__name__}")
    return errors


def check_no_residual_control_characters(record: StructuredLogRecord) -> list[str]:
    """Ensure cleaned text fields contain no remaining null or non-printable control characters."""
    errors: list[str] = []
    for field_name, value in [
        ("component", record.component),
        ("process_id", record.process_id),
        ("message", record.message),
    ]:
        if CONTROL_CHAR_CHECK_REGEX.search(value):
            errors.append(f"residual_control_character_in_{field_name}")
    return errors
