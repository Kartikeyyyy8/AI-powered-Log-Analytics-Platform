"""Canonical structured log schema for ML-ready output."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class StructuredLogRecord:
    """Canonical representation of a cleaned, validated, normalized log event."""

    event_id: str
    timestamp: str
    normalized_timestamp: str | None
    ingestion_timestamp: str
    component: str
    process_id: str
    message: str
    parsed_message_type: str | None
    extracted_metrics: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    line_number: int = 0
    raw_message: str = ""
    quality_flags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert structured log record to standard dictionary format."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "normalized_timestamp": self.normalized_timestamp,
            "ingestion_timestamp": self.ingestion_timestamp,
            "component": self.component,
            "process_id": self.process_id,
            "message": self.message,
            "parsed_message_type": self.parsed_message_type,
            "extracted_metrics": dict(self.extracted_metrics),
            "source": self.source,
            "line_number": self.line_number,
            "raw_message": self.raw_message,
            "quality_flags": list(self.quality_flags),
            "metadata": dict(self.metadata),
        }
