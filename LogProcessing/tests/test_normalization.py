import unittest

from LogProcessing.normalization.normalizer import LogNormalizer, ParsedTimestamp
from LogProcessing.parsing.base import ParsedLogRecord


class LogNormalizerTests(unittest.TestCase):
    def test_parses_8_digit_timestamp(self):
        parsed = LogNormalizer.parse_timestamp("20171223-22:15:29:606")
        self.assertIsNone(parsed.issue)
        self.assertEqual(parsed.normalized, "2017-12-23T22:15:29.606Z")

    def test_parses_6_digit_compact_timestamp(self):
        parsed = LogNormalizer.parse_timestamp("201812-19:39:28:966")
        self.assertIsNone(parsed.issue)
        self.assertEqual(parsed.normalized, "2018-01-02T19:39:28.966Z")

    def test_millisecond_normalization_regression(self):
        """P0 Regression tests: Non-padded milliseconds must not be right-zero-padded.

        :95 -> .095Z (95 ms, NOT 950 ms)
        :11 -> .011Z (11 ms, NOT 110 ms)
        :6  -> .006Z (6 ms, NOT 600 ms)
        """
        p95 = LogNormalizer.parse_timestamp("201813-9:59:0:95")
        self.assertIsNone(p95.issue)
        self.assertEqual(p95.normalized, "2018-01-03T09:59:00.095Z")

        p11 = LogNormalizer.parse_timestamp("201813-9:59:0:11")
        self.assertIsNone(p11.issue)
        self.assertEqual(p11.normalized, "2018-01-03T09:59:00.011Z")

        p6 = LogNormalizer.parse_timestamp("201813-9:59:0:6")
        self.assertIsNone(p6.issue)
        self.assertEqual(p6.normalized, "2018-01-03T09:59:00.006Z")

    def test_handles_invalid_timestamp_gracefully(self):
        parsed = LogNormalizer.parse_timestamp("invalid-timestamp-value")
        self.assertIsNone(parsed.normalized)
        self.assertEqual(parsed.issue, "timestamp_format_mismatch")

    def test_deterministic_event_id(self):
        id1 = LogNormalizer.generate_event_id("HealthApp.log", 42)
        id2 = LogNormalizer.generate_event_id("HealthApp.log", 42)
        self.assertEqual(id1, id2)
        self.assertEqual(id1, "healthapp_000042")

    def test_normalize_creates_structured_record(self):
        parsed = ParsedLogRecord(
            timestamp="20171223-22:15:29:606",
            component="Step_LSC",
            process_id="30002312",
            message="onStandStepChanged 3579",
            source="HealthApp.log",
            line_number=1,
            raw_message="20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579",
            ingestion_timestamp="2026-08-29T10:00:00Z",
        )

        structured = LogNormalizer.normalize(parsed)

        self.assertEqual(structured.event_id, "healthapp_000001")
        self.assertEqual(structured.normalized_timestamp, "2017-12-23T22:15:29.606Z")
        self.assertEqual(structured.parsed_message_type, "onStandStepChanged")
        self.assertEqual(structured.extracted_metrics, {"step_count": 3579})
        self.assertEqual(structured.component, "Step_LSC")
        self.assertEqual(structured.process_id, "30002312")


if __name__ == "__main__":
    unittest.main()
