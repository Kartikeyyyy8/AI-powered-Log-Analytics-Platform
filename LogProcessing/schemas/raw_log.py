"""Schema for raw log records emitted by ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RawLogRecord:
    """A single raw log line with ingestion metadata.

    The line has not been parsed or cleaned yet. It keeps enough source context
    for later dead-letter routing and audit-friendly data quality reports.
    """

    source_path: str
    source_name: str
    line_number: int
    raw_message: str
    ingestion_timestamp: str
    byte_size: int
    line_ending: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(
        cls,
        *,
        source_path: Path,
        line_number: int,
        raw_message: str,
        ingestion_timestamp: str,
        byte_size: int,
        line_ending: str,
        metadata: dict[str, Any] | None = None,
    ) -> "RawLogRecord":
        return cls(
            source_path=str(source_path),
            source_name=source_path.name,
            line_number=line_number,
            raw_message=raw_message,
            ingestion_timestamp=ingestion_timestamp,
            byte_size=byte_size,
            line_ending=line_ending,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "source_name": self.source_name,
            "line_number": self.line_number,
            "raw_message": self.raw_message,
            "ingestion_timestamp": self.ingestion_timestamp,
            "byte_size": self.byte_size,
            "line_ending": self.line_ending,
            "metadata": self.metadata,
        }

