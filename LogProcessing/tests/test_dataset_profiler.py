import tempfile
import unittest
from pathlib import Path

from LogProcessing.profiling.dataset_profiler import profile_dataset


class DatasetProfilerTests(unittest.TestCase):
    def test_profiles_healthapp_shape_and_message_pipes(self):
        content = (
            b"20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579\r\n"
            b"201812-19:39:28:966|Step_StandStepDataManager|30002312|"
            b"tryToReloadTodayBasicSteps1514893168960|0|14696|0\r\n"
            b"\r\n"
            b"\x00\x00bad-line\r\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.log"
            path.write_bytes(content)

            profile = profile_dataset(path)

        self.assertEqual(profile["record_counts"]["total_lines"], 4)
        self.assertEqual(profile["record_counts"]["valid_format_records"], 2)
        self.assertEqual(profile["record_counts"]["extra_separator_records"], 1)
        self.assertEqual(profile["record_counts"]["blank_lines"], 1)
        self.assertEqual(profile["record_counts"]["too_few_field_records"], 1)
        self.assertEqual(profile["record_counts"]["null_byte_lines"], 1)
        self.assertEqual(profile["timestamps"]["parseable_timestamps"], 2)


if __name__ == "__main__":
    unittest.main()
