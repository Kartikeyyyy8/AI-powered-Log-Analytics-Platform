"""Dedicated parser for HealthApp.log format."""

from __future__ import annotations

import re
from typing import Any

from LogProcessing.exceptions.errors import (
    BlankRecordError,
    MalformedRecordError,
    MissingFieldError,
)
from LogProcessing.parsing.base import BaseParser, ParsedLogRecord
from LogProcessing.schemas.raw_log import RawLogRecord

CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class HealthAppParser(BaseParser):
    """Parser specifically tuned for HealthApp.log dataset characteristics.

    Format expected:
        timestamp|component|process_id|message

    CRITICAL RULE:
        Splits strictly on the first 3 '|' separators using maxsplit=3,
        preserving any additional '|' characters inside the message payload.
    """

    def parse(self, raw_record: RawLogRecord) -> ParsedLogRecord:
        raw_text = raw_record.raw_message
        quality_flags: list[str] = []

        # Check metadata from ingestion or scan raw message
        if raw_record.metadata.get("contains_null_byte") or "\x00" in raw_text:
            quality_flags.append("contains_null_byte")

        if "\ufffd" in raw_text:
            quality_flags.append("decode_replacement_character")

        if CONTROL_CHARACTER_PATTERN.search(raw_text):
            quality_flags.append("contains_control_character")

        cleaned_text = raw_text.replace("\x00", "").strip()
        if not cleaned_text:
            raise BlankRecordError(f"Line {raw_record.line_number} is blank or null-only.")

        parts = raw_text.split("|", 3)
        pipe_count = raw_text.count("|")

        if len(parts) < 4:
            raise MalformedRecordError(
                f"Line {raw_record.line_number} has {len(parts)} fields, expected 4 (requires 3 pipe separators)."
            )

        if pipe_count > 3:
            quality_flags.append("message_contains_pipe_separator")

        timestamp, component, process_id, message = parts

        # Check for missing/empty required fields
        if not timestamp.strip():
            quality_flags.append("missing_timestamp")
            raise MissingFieldError(f"Line {raw_record.line_number} missing timestamp.")

        if not component.strip():
            quality_flags.append("missing_component")
            raise MissingFieldError(f"Line {raw_record.line_number} missing component.")

        if not process_id.strip():
            quality_flags.append("missing_process_id")
            raise MissingFieldError(f"Line {raw_record.line_number} missing process_id.")

        if not message.strip():
            quality_flags.append("missing_message")
            raise MissingFieldError(f"Line {raw_record.line_number} missing message.")

        return ParsedLogRecord(
            timestamp=timestamp.strip(),
            component=component.strip(),
            process_id=process_id.strip(),
            message=message.strip(),
            source=raw_record.source_name,
            line_number=raw_record.line_number,
            raw_message=raw_record.raw_message,
            ingestion_timestamp=raw_record.ingestion_timestamp,
            quality_flags=quality_flags,
            metadata={
                "pipe_count": pipe_count,
                "byte_size": raw_record.byte_size,
                "line_ending": raw_record.line_ending,
            },
        )
