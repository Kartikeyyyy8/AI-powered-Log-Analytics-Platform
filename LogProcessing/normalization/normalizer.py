"""Normalization utilities for timestamps, identifiers, and event structures."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from LogProcessing.parsing.base import ParsedLogRecord
from LogProcessing.parsing.message_classifier import MessageClassifier
from LogProcessing.schemas.structured_log import StructuredLogRecord

TIMESTAMP_PATTERN = re.compile(
    r"^(?P<date>\d{6,8})-(?P<hour>\d{1,2}):(?P<minute>\d{1,2}):"
    r"(?P<second>\d{1,2}):(?P<millisecond>\d{1,3})$"
)


class LogNormalizer:
    """Normalizes parsed and cleaned log records into canonical structured records."""

    @classmethod
    def parse_timestamp(cls, raw_timestamp: str) -> tuple[str | None, str | None]:
        """Parse HealthApp custom timestamp string into ISO 8601 UTC format.

        Supports both:
          - 8-digit dates: YYYYMMDD (e.g., 20171223)
          - 6-digit compact dates: YYYYMD (e.g., 201812 -> 2018-01-02, 201813 -> 2018-01-03)

        Returns:
            Tuple of (normalized_iso_timestamp_or_none, error_issue_or_none).
        """
        match = TIMESTAMP_PATTERN.match(raw_timestamp.strip())
        if not match:
            return None, "timestamp_format_mismatch"

        date_value = match.group("date")
        if len(date_value) == 8:
            year = int(date_value[:4])
            month = int(date_value[4:6])
            day = int(date_value[6:8])
        elif len(date_value) == 6:
            year = int(date_value[:4])
            month = int(date_value[4])
            day = int(date_value[5])
        else:
            return None, "unsupported_date_length"

        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        second = int(match.group("second"))
        
        # Right pad millisecond to 3 digits (e.g. '95' -> '950', '6' -> '600')
        ms_str = match.group("millisecond").ljust(3, "0")
        millisecond = int(ms_str)

        try:
            parsed = datetime(
                year,
                month,
                day,
                hour,
                minute,
                second,
                millisecond * 1000,
                tzinfo=timezone.utc,
            )
        except ValueError as exc:
            return None, f"invalid_datetime: {exc}"

        iso_formatted = (
            f"{parsed.year:04d}-{parsed.month:02d}-{parsed.day:02d}T"
            f"{parsed.hour:02d}:{parsed.minute:02d}:{parsed.second:02d}."
            f"{int(parsed.microsecond / 1000):03d}Z"
        )
        return iso_formatted, None

    @classmethod
    def generate_event_id(cls, source_name: str, line_number: int) -> str:
        """Generate a deterministic and stable event ID based on source and line number."""
        stem = Path(source_name).stem.lower().replace(" ", "_").replace("-", "_")
        prefix = stem if stem else "event"
        return f"{prefix}_{line_number:06d}"

    @classmethod
    def normalize(cls, record: ParsedLogRecord) -> StructuredLogRecord:
        """Transform a cleaned ParsedLogRecord into a canonical StructuredLogRecord."""
        flags = list(record.quality_flags)

        normalized_ts, ts_issue = cls.parse_timestamp(record.timestamp)
        if ts_issue is not None:
            if "timestamp_parse_failed" not in flags:
                flags.append("timestamp_parse_failed")

        event_id = cls.generate_event_id(record.source, record.line_number)
        msg_type, metrics = MessageClassifier.classify_and_extract(record.message)

        return StructuredLogRecord(
            event_id=event_id,
            timestamp=record.timestamp,
            normalized_timestamp=normalized_ts,
            ingestion_timestamp=record.ingestion_timestamp,
            component=record.component,
            process_id=record.process_id,
            message=record.message,
            parsed_message_type=msg_type,
            extracted_metrics=metrics,
            source=record.source,
            line_number=record.line_number,
            raw_message=record.raw_message,
            quality_flags=flags,
            metadata=dict(record.metadata),
        )
