import unittest
from pathlib import Path

from LogProcessing.exceptions.errors import BlankRecordError, MalformedRecordError, MissingFieldError
from LogProcessing.parsing.healthapp_parser import HealthAppParser
from LogProcessing.schemas.raw_log import RawLogRecord


class HealthAppParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = HealthAppParser()

    def _make_raw(self, msg: str, line_no: int = 1, null_byte: bool = False) -> RawLogRecord:
        return RawLogRecord.from_path(
            source_path=Path("HealthApp.log"),
            line_number=line_no,
            raw_message=msg,
            ingestion_timestamp="2026-08-29T10:00:00Z",
            byte_size=len(msg),
            line_ending="CRLF",
            metadata={"contains_null_byte": null_byte},
        )

    def test_parses_standard_four_field_record(self):
        raw = self._make_raw("20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579")
        parsed = self.parser.parse(raw)

        self.assertEqual(parsed.timestamp, "20171223-22:15:29:606")
        self.assertEqual(parsed.component, "Step_LSC")
        self.assertEqual(parsed.process_id, "30002312")
        self.assertEqual(parsed.message, "onStandStepChanged 3579")
        self.assertEqual(parsed.line_number, 1)
        self.assertEqual(parsed.quality_flags, [])

    def test_preserves_additional_pipes_in_message(self):
        msg = "201812-19:39:28:966|Step_StandStepDataManager|30002312|tryToReloadTodayBasicSteps1514893168960|0|14696|0"
        raw = self._make_raw(msg)
        parsed = self.parser.parse(raw)

        self.assertEqual(parsed.timestamp, "201812-19:39:28:966")
        self.assertEqual(parsed.component, "Step_StandStepDataManager")
        self.assertEqual(parsed.process_id, "30002312")
        self.assertEqual(parsed.message, "tryToReloadTodayBasicSteps1514893168960|0|14696|0")
        self.assertIn("message_contains_pipe_separator", parsed.quality_flags)

    def test_rejects_blank_or_whitespace_line(self):
        raw = self._make_raw("   \t  ")
        with self.assertRaises(BlankRecordError):
            self.parser.parse(raw)

    def test_rejects_too_few_fields(self):
        raw = self._make_raw("20171223-22:15:29:606|Step_LSC|only_two_separators")
        with self.assertRaises(MalformedRecordError):
            self.parser.parse(raw)

    def test_rejects_missing_fields(self):
        # Missing component
        raw1 = self._make_raw("20171223-22:15:29:606||30002312|msg")
        with self.assertRaises(MissingFieldError):
            self.parser.parse(raw1)

        # Missing timestamp
        raw2 = self._make_raw("|Step_LSC|30002312|msg")
        with self.assertRaises(MissingFieldError):
            self.parser.parse(raw2)

        # Missing process_id
        raw3 = self._make_raw("20171223-22:15:29:606|Step_LSC||msg")
        with self.assertRaises(MissingFieldError):
            self.parser.parse(raw3)

        # Missing message
        raw4 = self._make_raw("20171223-22:15:29:606|Step_LSC|30002312|")
        with self.assertRaises(MissingFieldError):
            self.parser.parse(raw4)

    def test_flags_null_bytes_and_control_characters(self):
        msg = "20171223-22:15:29:606|Step_LSC\x07|30002312|msg\x00data"
        raw = self._make_raw(msg, null_byte=True)
        parsed = self.parser.parse(raw)

        self.assertIn("contains_null_byte", parsed.quality_flags)
        self.assertIn("contains_control_character", parsed.quality_flags)


if __name__ == "__main__":
    unittest.main()
