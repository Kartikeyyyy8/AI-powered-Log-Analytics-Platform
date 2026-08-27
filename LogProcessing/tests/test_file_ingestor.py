import tempfile
import unittest
from pathlib import Path

from LogProcessing.exceptions.errors import (
    EmptyLogFileError,
    InputFileNotFoundError,
    LogFileTooLargeError,
    UnsupportedLogFileError,
)
from LogProcessing.ingestion.file_ingestor import FileIngestor


class FileIngestorTests(unittest.TestCase):
    def test_streams_raw_records_with_source_metadata(self):
        content = (
            b"20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579\r\n"
            b"\x00corrupted-but-readable|Step_Test|1|message\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "HealthApp.log"
            path.write_bytes(content)

            records = list(FileIngestor().ingest_file(path))

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].source_name, "HealthApp.log")
        self.assertEqual(records[0].line_number, 1)
        self.assertEqual(records[0].line_ending, "CRLF")
        self.assertEqual(records[0].metadata["encoding"], "utf-8")
        self.assertFalse(records[0].metadata["contains_null_byte"])
        self.assertEqual(records[1].line_number, 2)
        self.assertEqual(records[1].line_ending, "LF")
        self.assertTrue(records[1].metadata["contains_null_byte"])

    def test_streams_multiple_files_in_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir) / "first.log"
            second = Path(tmpdir) / "second.txt"
            first.write_text("one\n", encoding="utf-8")
            second.write_text("two\n", encoding="utf-8")

            records = list(FileIngestor().ingest_files([first, second]))

        self.assertEqual([record.raw_message for record in records], ["one", "two"])
        self.assertEqual([record.source_name for record in records], ["first.log", "second.txt"])

    def test_rejects_missing_file(self):
        with self.assertRaises(InputFileNotFoundError):
            list(FileIngestor().ingest_file("/tmp/does-not-exist-healthapp.log"))

    def test_rejects_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.log"
            path.write_text("", encoding="utf-8")

            with self.assertRaises(EmptyLogFileError):
                list(FileIngestor().ingest_file(path))

    def test_rejects_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "HealthApp.csv"
            path.write_text("log\n", encoding="utf-8")

            with self.assertRaises(UnsupportedLogFileError):
                list(FileIngestor().ingest_file(path))

    def test_rejects_file_above_configured_size_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "large.log"
            path.write_text("too large\n", encoding="utf-8")

            with self.assertRaises(LogFileTooLargeError):
                list(FileIngestor(max_file_size_bytes=1).ingest_file(path))


if __name__ == "__main__":
    unittest.main()
