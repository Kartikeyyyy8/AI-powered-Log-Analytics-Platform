import unittest

from LogProcessing.cleaning.cleaner import LogCleaner
from LogProcessing.parsing.base import ParsedLogRecord


class LogCleanerTests(unittest.TestCase):
    def test_clean_text_removes_null_bytes_and_control_chars(self):
        dirty = "\x00\x01Hello\x07 World\x00"
        cleaned, flags = LogCleaner.clean_text(dirty)

        self.assertEqual(cleaned, "Hello World")
        self.assertIn("cleaned_null_bytes", flags)
        self.assertIn("cleaned_control_characters", flags)

    def test_clean_text_leaves_clean_text_untouched(self):
        clean = "Normal text message 123"
        cleaned, flags = LogCleaner.clean_text(clean)

        self.assertEqual(cleaned, clean)
        self.assertEqual(flags, [])

    def test_clean_record_preserves_raw_message(self):
        raw_msg = "\x0020171223-22:15:29:606|Step_LSC\x07|30002312|msg\x00"
        record = ParsedLogRecord(
            timestamp="\x0020171223-22:15:29:606",
            component="Step_LSC\x07",
            process_id="30002312",
            message="msg\x00",
            source="HealthApp.log",
            line_number=10,
            raw_message=raw_msg,
            ingestion_timestamp="2026-08-29T10:00:00Z",
            quality_flags=["contains_null_byte"],
        )

        cleaned = LogCleaner.clean_record(record)

        self.assertEqual(cleaned.timestamp, "20171223-22:15:29:606")
        self.assertEqual(cleaned.component, "Step_LSC")
        self.assertEqual(cleaned.process_id, "30002312")
        self.assertEqual(cleaned.message, "msg")
        self.assertEqual(cleaned.raw_message, raw_msg)  # Raw preserved
        self.assertIn("cleaned_null_bytes", cleaned.quality_flags)
        self.assertIn("cleaned_control_characters", cleaned.quality_flags)


if __name__ == "__main__":
    unittest.main()
