"""Regression and integration tests specifically asserting real HealthApp dataset guarantees."""

import json
import tempfile
import unittest
from pathlib import Path

from LogProcessing.services.pipeline import process_logs

HEALTHAPP_DATASET_PATH = Path("/Users/namansehwag/Downloads/HealthApp.log")


class RealDatasetRegressionTests(unittest.TestCase):
    @unittest.skipUnless(
        HEALTHAPP_DATASET_PATH.exists(), "Real HealthApp.log not available at expected path"
    )
    def test_real_healthapp_dataset_guarantees(self):
        """Verify real dataset execution against all Cursor audit findings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "outputs"

            result = process_logs(
                input_path=HEALTHAPP_DATASET_PATH,
                output_dir=out_dir,
                generate_profile=False,
            )

            # 1. Total counts reconciliation
            self.assertEqual(result.total_records, 253395)
            self.assertEqual(result.valid_records, 253394)
            self.assertEqual(result.invalid_records, 1)
            self.assertEqual(result.valid_records + result.invalid_records, result.total_records)

            # 2. Quality report metrics
            report = json.loads(result.quality_report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["total_lines"], 253395)
            self.assertEqual(report["valid_records"], 253394)
            self.assertEqual(report["invalid_records"], 1)
            self.assertEqual(report["corrupted_lines"], 1)
            self.assertEqual(report["extra_separator_records"], 20)

            # 3. Dead letter contains the corrupted line 238724
            dead_lines = result.dead_letter_logs_path.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(dead_lines), 1)
            dead_record = json.loads(dead_lines[0])
            self.assertEqual(dead_record["line_number"], 238724)
            self.assertIn("contains null bytes", dead_record["error_reason"])
            self.assertIn("\x00", dead_record["raw_message"])

            # 4. Spot check millisecond normalization on line 253395 (ending with :95)
            # Read last line of processed_logs.jsonl
            with open(result.processed_logs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                last_record = json.loads(lines[-1])
                self.assertEqual(last_record["line_number"], 253395)
                self.assertEqual(last_record["timestamp"], "201813-9:59:0:95")
                self.assertEqual(last_record["normalized_timestamp"], "2018-01-03T09:59:00.095Z")

            # 5. Spot check extra pipe record (around line 1794)
            with open(result.processed_logs_path, "r", encoding="utf-8") as f:
                # Line 1794 is at index 1793 in the valid records list (since all preceding records were valid)
                rec_1794 = json.loads(lines[1793])
                self.assertEqual(rec_1794["line_number"], 1794)
                self.assertEqual(
                    rec_1794["message"],
                    "tryToReloadTodayBasicSteps1514044800223|3786|0|0",
                )
                self.assertEqual(
                    rec_1794["parsed_message_type"], "tryToReloadTodayBasicSteps"
                )
                self.assertIn("message_contains_pipe_separator", rec_1794["quality_flags"])


if __name__ == "__main__":
    unittest.main()
