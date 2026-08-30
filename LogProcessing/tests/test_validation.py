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

    def test_record_with_null_bytes_is_rejected(self):
        """P0 Regression test: Null-byte corrupted records must NOT pass validation."""
        rec = StructuredLogRecord(
            event_id="healthapp_238724",
            timestamp="201812-19:39:28:633",
            normalized_timestamp="2018-01-02T19:39:28.633Z",
            ingestion_timestamp="2026-08-29T10:00:00Z",
            component="Step_StaticReceiver",
            process_id="30002312",
            message="onReceive action: android.intent.action.BOOT_COMPLETED",
            parsed_message_type="BOOT_COMPLETED",
            source="HealthApp.log",
            line_number=238724,
            raw_message="\x00\x00corrupted-line",
            quality_flags=["contains_null_byte", "cleaned_null_bytes"],
        )
        is_valid, errors = self.validator.validate(rec)
        self.assertFalse(is_valid)
        self.assertTrue(any("contains null bytes" in e for e in errors))

    def test_unparseable_timestamp_is_rejected(self):
        rec = StructuredLogRecord(
            event_id="healthapp_000001",
            timestamp="invalid_ts",
            normalized_timestamp=None,
            ingestion_timestamp="2026-08-29T10:00:00Z",
            component="Step_LSC",
            process_id="30002312",
            message="msg",
            parsed_message_type=None,
            source="HealthApp.log",
            line_number=1,
            raw_message="invalid_ts|Step_LSC|30002312|msg",
            quality_flags=["timestamp_parse_failed"],
        )
        is_valid, errors = self.validator.validate(rec)
        self.assertFalse(is_valid)
        self.assertTrue(any("timestamp" in e.lower() for e in errors))

    def test_extra_pipes_in_message_remains_valid(self):
        """Extra pipes in payload message are valid and not rejected."""
        rec = StructuredLogRecord(
            event_id="healthapp_001794",
            timestamp="20171224-0:0:0:234",
            normalized_timestamp="2017-12-24T00:00:00.234Z",
            ingestion_timestamp="2026-08-29T10:00:00Z",
            component="Step_StandStepDataManager",
            process_id="30002312",
            message="tryToReloadTodayBasicSteps1514044800223|3786|0|0",
            parsed_message_type="tryToReloadTodayBasicSteps",
            extracted_metrics={"timestamp_ms": 1514044800223, "step_count": 3786},
            source="HealthApp.log",
            line_number=1794,
            raw_message="20171224-0:0:0:234|Step_StandStepDataManager|30002312|tryToReloadTodayBasicSteps1514044800223|3786|0|0",
            quality_flags=["message_contains_pipe_separator"],
        )
        is_valid, errors = self.validator.validate(rec)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_missing_field_fails(self):
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
            raw_message="20171223-22:15:29:606||30002312|msg",
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
            raw_message="20171223-22:15:29:606|Step_LSC|30002312|msg",
        )
        is_valid, errors = self.validator.validate(rec)
        self.assertFalse(is_valid)
        self.assertTrue(any("invalid_line_number" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
