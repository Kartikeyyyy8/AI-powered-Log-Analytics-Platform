"""Streaming JSON Lines storage writer for processed structured logs."""

from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any

from LogProcessing.exceptions.errors import StorageError
from LogProcessing.schemas.structured_log import StructuredLogRecord


class JsonLinesWriter:
    """Incrementally writes records to a JSON Lines (.jsonl) file."""

    def __init__(self, output_path: str | Path) -> None:
        self.path = Path(output_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = None
        self.written_count = 0

    def __enter__(self) -> "JsonLinesWriter":
        try:
            self._handle = self.path.open("w", encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Failed to open output file {self.path}: {exc}") from exc
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._handle:
            self._handle.close()
            self._handle = None

    def write(self, record: StructuredLogRecord | dict[str, Any]) -> None:
        """Write a single structured record as one JSON line."""
        if not self._handle:
            raise StorageError("Writer is not open. Use within a context manager.")

        data = record.to_dict() if hasattr(record, "to_dict") else record
        line = json.dumps(data, ensure_ascii=False) + "\n"
        self._handle.write(line)
        self.written_count += 1

    def flush(self) -> None:
        """Flush the underlying stream."""
        if self._handle:
            self._handle.flush()


def write_json_report(report_data: dict[str, Any], output_path: str | Path) -> Path:
    """Write an arbitrary JSON report with pretty indentation."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as exc:
        raise StorageError(f"Failed to write report to {path}: {exc}") from exc
    return path
