"""Domain-specific errors used by the log processing pipeline."""

from __future__ import annotations


class LogProcessingError(Exception):
    """Base exception for the LogProcessing module."""


class IngestionError(LogProcessingError):
    """Raised when raw logs cannot be ingested safely."""


class InputFileNotFoundError(IngestionError):
    """Raised when an input log file does not exist."""


class InputFileTypeError(IngestionError):
    """Raised when an input path is not a regular file."""


class UnsupportedLogFileError(IngestionError):
    """Raised when a file extension is not supported by the ingestor."""


class EmptyLogFileError(IngestionError):
    """Raised when a log file has no content."""


class LogFileTooLargeError(IngestionError):
    """Raised when a file exceeds the configured ingestion size limit."""

