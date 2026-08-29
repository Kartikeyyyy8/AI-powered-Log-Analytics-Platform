"""Quality analyzer for aggregating metrics and producing reports."""

from __future__ import annotations

from LogProcessing.quality.metrics import PipelineQualityMetrics
from LogProcessing.schemas.dead_letter_log import DeadLetterLogRecord
from LogProcessing.schemas.quality_report import QualityReport
from LogProcessing.schemas.structured_log import StructuredLogRecord


class QualityAnalyzer:
    """Collects and computes data quality metrics as logs stream through the pipeline."""

    def __init__(self) -> None:
        self.metrics = PipelineQualityMetrics()

    def record_processed_record(self, record: StructuredLogRecord) -> None:
        """Update metrics for a successfully normalized and validated record."""
        self.metrics.processed_records += 1
        self.metrics.valid_records += 1

        self.metrics.component_counts[record.component or "UNKNOWN"] += 1
        self.metrics.message_type_counts[record.parsed_message_type or "UNKNOWN"] += 1

        for flag in record.quality_flags:
            self.metrics.quality_flag_counts[flag] += 1
            if flag == "timestamp_parse_failed":
                self.metrics.timestamp_parse_failures += 1
            elif flag == "message_contains_pipe_separator":
                self.metrics.extra_separator_records += 1
            elif flag in ("contains_null_byte", "cleaned_null_bytes"):
                self.metrics.corrupted_lines += 1

    def record_dead_letter(self, dead_letter: DeadLetterLogRecord) -> None:
        """Update metrics for an unparseable or rejected record."""
        self.metrics.processed_records += 1
        self.metrics.invalid_records += 1

        reason = dead_letter.error_reason.lower()
        if "blank" in reason:
            self.metrics.blank_lines += 1
        if "null" in reason or "corrupt" in reason or "malformed" in reason:
            self.metrics.corrupted_lines += 1
        if "missing" in reason:
            self.metrics.missing_field_counts[dead_letter.error_reason] += 1

        for flag in dead_letter.quality_flags:
            self.metrics.quality_flag_counts[flag] += 1

    def generate_report(self, total_lines: int | None = None) -> QualityReport:
        """Compile accumulated metrics into a structured QualityReport."""
        if total_lines is not None:
            self.metrics.total_lines = total_lines
        else:
            self.metrics.total_lines = self.metrics.processed_records

        return QualityReport(
            total_lines=self.metrics.total_lines,
            processed_records=self.metrics.processed_records,
            valid_records=self.metrics.valid_records,
            invalid_records=self.metrics.invalid_records,
            blank_lines=self.metrics.blank_lines,
            corrupted_lines=self.metrics.corrupted_lines,
            timestamp_parse_failures=self.metrics.timestamp_parse_failures,
            extra_separator_records=self.metrics.extra_separator_records,
            component_counts=dict(self.metrics.component_counts),
            message_type_counts=dict(self.metrics.message_type_counts),
            missing_field_counts=dict(self.metrics.missing_field_counts),
            quality_flag_counts=dict(self.metrics.quality_flag_counts),
        )
