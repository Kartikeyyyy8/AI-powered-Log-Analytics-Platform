import unittest

from LogProcessing.schemas.structured_log import StructuredLogRecord
from LogProcessing.validation.validator import LogValidator


class LogValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = LogValidator()

    def _valid_record(self) -> StructuredLogRecord:
        return StructuredLogRecord(
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
            raw_message="20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579",
        )

    def test_valid_record_passes(self):
        rec = self._valid_record()
        is_valid, errors = self.validator.validate(rec)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_missing_field_fails(self):
        # Missing component
        rec = StructuredLogRecord(
            event_id="healthapp_000001",
            timestamp="20171223-22:15:29:606",
            normalized_timestamp="2017-12-23T22:15:29.606Z",
            ingestion_timestamp="2026-08-29T10:00:00Z",
            component="",
            process_id="30002312",
            message="msg",
            parsed_message_type=None,
            source="HealthApp.log",
            line_number=1,
        )
        is_valid, errors = self.validator.validate(rec)
        self.assertFalse(is_valid)
        self.assertTrue(any("missing_required_field: component" in e for e in errors))

    def test_negative_line_number_fails(self):
        rec = StructuredLogRecord(
            event_id="healthapp_000001",
            timestamp="20171223-22:15:29:606",
            normalized_timestamp="2017-12-23T22:15:29.606Z",
            ingestion_timestamp="2026-08-29T10:00:00Z",
            component="Step_LSC",
            process_id="30002312",
            message="msg",
            parsed_message_type=None,
            source="HealthApp.log",
            line_number=-5,
        )
        is_valid, errors = self.validator.validate(rec)
        self.assertFalse(is_valid)
        self.assertTrue(any("invalid_line_number" in e for e in errors))

    def test_residual_control_characters_fail(self):
        rec = StructuredLogRecord(
            event_id="healthapp_000001",
            timestamp="20171223-22:15:29:606",
            normalized_timestamp="2017-12-23T22:15:29.606Z",
            ingestion_timestamp="2026-08-29T10:00:00Z",
            component="Step_LSC",
            process_id="30002312",
            message="msg\x00with_null",
            parsed_message_type=None,
            source="HealthApp.log",
            line_number=1,
        )
        is_valid, errors = self.validator.validate(rec)
        self.assertFalse(is_valid)
        self.assertTrue(any("residual_control_character_in_message" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
