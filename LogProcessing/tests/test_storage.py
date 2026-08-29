import json
import tempfile
import unittest
from pathlib import Path

from LogProcessing.schemas.dead_letter_log import DeadLetterLogRecord
from LogProcessing.schemas.structured_log import StructuredLogRecord
from LogProcessing.storage.dead_letter import DeadLetterWriter
from LogProcessing.storage.writer import JsonLinesWriter, write_json_report


class StorageTests(unittest.TestCase):
    def test_json_lines_writer_writes_incrementally(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "output.jsonl"
            rec = StructuredLogRecord(
                event_id="healthapp_000001",
                timestamp="20171223-22:15:29:606",
                normalized_timestamp="2017-12-23T22:15:29.606Z",
                ingestion_timestamp="2026-08-29T10:00:00Z",
                component="Step_LSC",
                process_id="30002312",
                message="onStandStepChanged 3579",
                parsed_message_type="onStandStepChanged",
                source="HealthApp.log",
                line_number=1,
            )

            with JsonLinesWriter(out_file) as writer:
                writer.write(rec)

            self.assertTrue(out_file.exists())
            lines = out_file.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 1)
            loaded = json.loads(lines[0])
            self.assertEqual(loaded["event_id"], "healthapp_000001")
            self.assertEqual(loaded["component"], "Step_LSC")

    def test_dead_letter_writer_writes_dead_letters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "dead_letter.jsonl"
            rec = DeadLetterLogRecord(
                source="HealthApp.log",
                line_number=5,
                raw_message="bad line",
                error_reason="malformed_line",
                ingestion_timestamp="2026-08-29T10:00:00Z",
            )

            with DeadLetterWriter(out_file) as writer:
                writer.write(rec)

            self.assertTrue(out_file.exists())
            lines = out_file.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 1)
            loaded = json.loads(lines[0])
            self.assertEqual(loaded["error_reason"], "malformed_line")

    def test_write_json_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "report.json"
            data = {"total": 10, "valid": 10}
            path = write_json_report(data, out_file)

            self.assertTrue(path.exists())
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, data)


if __name__ == "__main__":
    unittest.main()
