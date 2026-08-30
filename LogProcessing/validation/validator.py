"""Validator for structured log records."""

from __future__ import annotations

from LogProcessing.schemas.structured_log import StructuredLogRecord
from LogProcessing.validation.rules import (
    check_corruption_policy,
    check_extracted_metrics,
    check_line_number,
    check_no_residual_control_characters,
    check_required_fields,
)


class LogValidator:
    """Validates structured log records against data contracts and quality rules."""

    def __init__(self) -> None:
        self.rules = [
            check_required_fields,
            check_line_number,
            check_corruption_policy,
            check_extracted_metrics,
            check_no_residual_control_characters,
        ]

    def validate(self, record: StructuredLogRecord) -> tuple[bool, list[str]]:
        """Validate a record against all rules.

        Returns:
            Tuple of (is_valid: bool, error_reasons: list[str]).
        """
        all_errors: list[str] = []
        for rule in self.rules:
            errors = rule(record)
            if errors:
                all_errors.extend(errors)

        return (len(all_errors) == 0, all_errors)
