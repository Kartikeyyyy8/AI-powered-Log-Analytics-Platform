import json
import tempfile
import unittest
from pathlib import Path

from LogProcessing.services.pipeline import process_logs


class PipelineTests(unittest.TestCase):
    def test_end_to_end_pipeline_with_real_world_edge_cases(self):
        # Sample dataset containing:
        # 1. Normal record
        # 2. Record with extra pipes in message
        # 3. Blank line
        # 4. Corrupted record with null bytes
        # 5. Record missing component
        content = (
            b"20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579\r\n"
            b"201812-19:39:28:966|Step_StandStepDataManager|30002312|tryToReloadTodayBasicSteps1514893168960|0|14696|0\r\n"
            b"\r\n"
            b"\x00\x00corrupted-record-here\r\n"
            b"20171223-22:15:30:000||30002312|missing component\r\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            input_log = Path(tmpdir) / "HealthApp.log"
            input_log.write_bytes(content)

            out_dir = Path(tmpdir) / "outputs"

            result = process_logs(input_log, output_dir=out_dir, generate_profile=True)

            self.assertEqual(result.total_records, 5)
            self.assertEqual(result.valid_records, 2)
            self.assertEqual(result.invalid_records, 3)

            # Check processed logs
            self.assertTrue(result.processed_logs_path.exists())
            processed_lines = result.processed_logs_path.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(processed_lines), 2)
            rec1 = json.loads(processed_lines[0])
            self.assertEqual(rec1["component"], "Step_LSC")
            self.assertEqual(rec1["parsed_message_type"], "onStandStepChanged")
            self.assertEqual(rec1["extracted_metrics"], {"step_count": 3579})

            rec2 = json.loads(processed_lines[1])
            self.assertEqual(rec2["component"], "Step_StandStepDataManager")
            self.assertEqual(rec2["parsed_message_type"], "tryToReloadTodayBasicSteps")
            self.assertIn("message_contains_pipe_separator", rec2["quality_flags"])

            # Check dead letter logs
            self.assertTrue(result.dead_letter_logs_path.exists())
            dead_lines = result.dead_letter_logs_path.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(dead_lines), 3)

            # Check quality report
            self.assertTrue(result.quality_report_path.exists())
            report = json.loads(result.quality_report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["total_lines"], 5)
            self.assertEqual(report["valid_records"], 2)
            self.assertEqual(report["invalid_records"], 3)
            self.assertEqual(report["blank_lines"], 1)

            # Check dataset profile
            self.assertTrue(result.dataset_profile_path.exists())


if __name__ == "__main__":
    unittest.main()
