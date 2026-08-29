"""Data-aware cleaning module for log records."""

from __future__ import annotations

import re
from dataclasses import replace

from LogProcessing.parsing.base import ParsedLogRecord

CONTROL_CHARACTERS_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class LogCleaner:
    """Cleans log fields while preserving raw data and tagging quality flags."""

    @classmethod
    def clean_text(cls, text: str) -> tuple[str, list[str]]:
        """Clean a single string of null bytes and unprintable control characters.

        Returns:
            Tuple of (cleaned_text, list_of_applied_flags).
        """
        flags: list[str] = []
        cleaned = text

        if "\x00" in cleaned:
            cleaned = cleaned.replace("\x00", "")
            flags.append("cleaned_null_bytes")

        if CONTROL_CHARACTERS_REGEX.search(cleaned):
            cleaned = CONTROL_CHARACTERS_REGEX.sub("", cleaned)
            flags.append("cleaned_control_characters")

        stripped = cleaned.strip()
        if stripped != cleaned:
            cleaned = stripped

        return cleaned, flags

    @classmethod
    def clean_record(cls, record: ParsedLogRecord) -> ParsedLogRecord:
        """Clean all text fields in a parsed log record.

        Original raw_message and source metadata are preserved unmodified.
        """
        all_flags = list(record.quality_flags)

        clean_ts, ts_flags = cls.clean_text(record.timestamp)
        clean_comp, comp_flags = cls.clean_text(record.component)
        clean_pid, pid_flags = cls.clean_text(record.process_id)
        clean_msg, msg_flags = cls.clean_text(record.message)

        for flag in ts_flags + comp_flags + pid_flags + msg_flags:
            if flag not in all_flags:
                all_flags.append(flag)

        return replace(
            record,
            timestamp=clean_ts,
            component=clean_comp,
            process_id=clean_pid,
            message=clean_msg,
            quality_flags=all_flags,
        )
