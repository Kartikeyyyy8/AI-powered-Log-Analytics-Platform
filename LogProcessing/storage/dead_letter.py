"""Streaming storage handler for dead-letter records."""

from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType
from typing import Any

from LogProcessing.exceptions.errors import StorageError
from LogProcessing.schemas.dead_letter_log import DeadLetterLogRecord


class DeadLetterWriter:
    """Incrementally writes unparseable or rejected records to dead_letter_logs.jsonl."""

    def __init__(self, output_path: str | Path) -> None:
        self.path = Path(output_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = None
        self.written_count = 0

    def __enter__(self) -> "DeadLetterWriter":
        try:
            self._handle = self.path.open("w", encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Failed to open dead letter file {self.path}: {exc}") from exc
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

    def write(self, record: DeadLetterLogRecord | dict[str, Any]) -> None:
        """Write a single dead-letter record as one JSON line."""
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
