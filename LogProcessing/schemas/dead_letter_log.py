"""Schema for records that failed parsing or validation (dead-letter queue)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DeadLetterLogRecord:
    """Represents an unparseable or invalid log record routed to dead-letter storage."""

    source: str
    line_number: int
    raw_message: str
    error_reason: str
    ingestion_timestamp: str
    quality_flags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert dead letter record to standard dictionary format."""
        return {
            "source": self.source,
            "line_number": self.line_number,
            "raw_message": self.raw_message,
            "error_reason": self.error_reason,
            "ingestion_timestamp": self.ingestion_timestamp,
            "quality_flags": list(self.quality_flags),
            "metadata": dict(self.metadata),
        }
