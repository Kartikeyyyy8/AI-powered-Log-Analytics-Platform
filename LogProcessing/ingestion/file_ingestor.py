"""Streaming file ingestor for raw log datasets."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path

from LogProcessing.exceptions.errors import (
    EmptyLogFileError,
    InputFileNotFoundError,
    InputFileTypeError,
    LogFileTooLargeError,
    UnsupportedLogFileError,
)
from LogProcessing.ingestion.base import BaseIngestor
from LogProcessing.schemas.raw_log import RawLogRecord

DEFAULT_SUPPORTED_EXTENSIONS = frozenset({".log", ".txt", ".jsonl"})
DEFAULT_MAX_FILE_SIZE_BYTES = 512 * 1024 * 1024


class FileIngestor(BaseIngestor):
    """Read raw logs line by line with source metadata.

    The ingestor opens files in binary mode. That keeps line-ending and byte-size
    metadata accurate and lets later cleaning stages detect null/control bytes.
    """

    def __init__(
        self,
        *,
        supported_extensions: Iterable[str] | None = None,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        encoding: str = "utf-8",
    ) -> None:
        self.supported_extensions = frozenset(
            extension.lower() for extension in (supported_extensions or DEFAULT_SUPPORTED_EXTENSIONS)
        )
        self.max_file_size_bytes = max_file_size_bytes
        self.encoding = encoding

    def ingest_file(
        self, input_path: str | Path, ingestion_timestamp: str | None = None
    ) -> Iterator[RawLogRecord]:
        path = Path(input_path)
        self._validate_file(path)
        batch_ts = ingestion_timestamp or self._utc_now()

        with path.open("rb") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                yield RawLogRecord.from_path(
                    source_path=path,
                    line_number=line_number,
                    raw_message=self._decode_line(raw_line),
                    ingestion_timestamp=batch_ts,
                    byte_size=len(raw_line),
                    line_ending=self._line_ending(raw_line),
                    metadata={
                        "encoding": self.encoding,
                        "contains_null_byte": b"\x00" in raw_line,
                    },
                )

    def ingest_files(
        self, input_paths: Iterable[str | Path], ingestion_timestamp: str | None = None
    ) -> Iterator[RawLogRecord]:
        batch_ts = ingestion_timestamp or self._utc_now()
        for input_path in input_paths:
            yield from self.ingest_file(input_path, ingestion_timestamp=batch_ts)

    def _validate_file(self, path: Path) -> None:
        if not path.exists():
            raise InputFileNotFoundError(f"Input log file does not exist: {path}")
        if not path.is_file():
            raise InputFileTypeError(f"Input path is not a file: {path}")
        if path.suffix.lower() not in self.supported_extensions:
            raise UnsupportedLogFileError(
                f"Unsupported log file extension '{path.suffix}'. "
                f"Supported extensions: {sorted(self.supported_extensions)}"
            )

        file_size = path.stat().st_size
        if file_size == 0:
            raise EmptyLogFileError(f"Input log file is empty: {path}")
        if file_size > self.max_file_size_bytes:
            raise LogFileTooLargeError(
                f"Input log file is {file_size} bytes, above the configured limit "
                f"of {self.max_file_size_bytes} bytes: {path}"
            )

    def _decode_line(self, raw_line: bytes) -> str:
        return raw_line.decode(self.encoding, errors="replace").rstrip("\r\n")

    @staticmethod
    def _line_ending(raw_line: bytes) -> str:
        if raw_line.endswith(b"\r\n"):
            return "CRLF"
        if raw_line.endswith(b"\n"):
            return "LF"
        if raw_line.endswith(b"\r"):
            return "CR"
        return "NONE"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
