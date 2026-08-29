"""Schema for data quality report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class QualityReport:
    """Aggregate quality metrics across a processed dataset."""

    total_lines: int = 0
    processed_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    blank_lines: int = 0
    corrupted_lines: int = 0
    timestamp_parse_failures: int = 0
    extra_separator_records: int = 0
    component_counts: dict[str, int] = field(default_factory=dict)
    message_type_counts: dict[str, int] = field(default_factory=dict)
    missing_field_counts: dict[str, int] = field(default_factory=dict)
    quality_flag_counts: dict[str, int] = field(default_factory=dict)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert quality report to standard dictionary format."""
        return {
            "total_lines": self.total_lines,
            "processed_records": self.processed_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "blank_lines": self.blank_lines,
            "corrupted_lines": self.corrupted_lines,
            "timestamp_parse_failures": self.timestamp_parse_failures,
            "extra_separator_records": self.extra_separator_records,
            "component_counts": self.component_counts,
            "message_type_counts": self.message_type_counts,
            "missing_field_counts": self.missing_field_counts,
            "quality_flag_counts": self.quality_flag_counts,
            "generated_at": self.generated_at,
        }
