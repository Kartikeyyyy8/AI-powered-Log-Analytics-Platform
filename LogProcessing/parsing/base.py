"""Base interface and data contracts for log parsing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from LogProcessing.schemas.raw_log import RawLogRecord


@dataclass(frozen=True)
class ParsedLogRecord:
    """Intermediate representation of parsed record before normalization/validation."""

    timestamp: str
    component: str
    process_id: str
    message: str
    source: str
    line_number: int
    raw_message: str
    ingestion_timestamp: str
    quality_flags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    """Abstract parser interface."""

    @abstractmethod
    def parse(self, raw_record: RawLogRecord) -> ParsedLogRecord:
        """Parse a raw log record into a structured representation.

        Raises:
            ParsingError: If record is malformed and cannot be parsed.
        """
