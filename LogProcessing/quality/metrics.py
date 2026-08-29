"""Quality metrics data containers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class PipelineQualityMetrics:
    """Accumulator for dataset quality metrics during pipeline execution."""

    total_lines: int = 0
    processed_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    blank_lines: int = 0
    corrupted_lines: int = 0
    timestamp_parse_failures: int = 0
    extra_separator_records: int = 0
    component_counts: Counter[str] = field(default_factory=Counter)
    message_type_counts: Counter[str] = field(default_factory=Counter)
    missing_field_counts: Counter[str] = field(default_factory=Counter)
    quality_flag_counts: Counter[str] = field(default_factory=Counter)
