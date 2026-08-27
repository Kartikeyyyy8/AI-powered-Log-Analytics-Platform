"""Base interfaces for log ingestion sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from LogProcessing.schemas.raw_log import RawLogRecord


class BaseIngestor(ABC):
    """Common contract for current and future ingestion sources."""

    @abstractmethod
    def ingest_file(self, input_path: str | Path) -> Iterable[RawLogRecord]:
        """Yield raw records from one input file."""

    @abstractmethod
    def ingest_files(self, input_paths: Iterable[str | Path]) -> Iterable[RawLogRecord]:
        """Yield raw records from multiple input files."""

