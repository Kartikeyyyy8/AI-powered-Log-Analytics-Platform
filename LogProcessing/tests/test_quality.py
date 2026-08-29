import unittest

from LogProcessing.quality.analyzer import QualityAnalyzer
from LogProcessing.schemas.dead_letter_log import DeadLetterLogRecord
from LogProcessing.schemas.structured_log import StructuredLogRecord


class QualityAnalyzerTests(unittest.TestCase):
    def test_aggregates_valid_and_dead_letter_records(self):
        analyzer = QualityAnalyzer()

        valid_rec = StructuredLogRecord(
            event_id="healthapp_000001",
            timestamp="20171223-22:15:29:606",
            normalized_timestamp="2017-12-23T22:15:29.606Z",
            ingestion_timestamp="2026-08-29T10:00:00Z",
            component="Step_LSC",
            process_id="30002312",
            message="onStandStepChanged 3579",
            parsed_message_type="onStandStepChanged",
            extracted_metrics={"step_count": 3579},
            source="HealthApp.log",
            line_number=1,
            quality_flags=["message_contains_pipe_separator"],
        )

        dead_rec = DeadLetterLogRecord(
            source="HealthApp.log",
            line_number=2,
            raw_message="blank",
            error_reason="blank_line",
            ingestion_timestamp="2026-08-29T10:00:00Z",
            quality_flags=["blank_line"],
        )

        analyzer.record_processed_record(valid_rec)
        analyzer.record_dead_letter(dead_rec)

        report = analyzer.generate_report()

        self.assertEqual(report.total_lines, 2)
        self.assertEqual(report.valid_records, 1)
        self.assertEqual(report.invalid_records, 1)
        self.assertEqual(report.blank_lines, 1)
        self.assertEqual(report.extra_separator_records, 1)
        self.assertEqual(report.component_counts["Step_LSC"], 1)
        self.assertEqual(report.message_type_counts["onStandStepChanged"], 1)


if __name__ == "__main__":
    unittest.main()
