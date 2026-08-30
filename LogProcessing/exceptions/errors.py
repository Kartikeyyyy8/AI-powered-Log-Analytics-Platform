"""Domain-specific errors used by the log processing pipeline."""

from __future__ import annotations


class LogProcessingError(Exception):
    """Base exception for the LogProcessing module."""


# Ingestion Errors
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


# Parsing Errors
class ParsingError(LogProcessingError):
    """Raised when a raw log record cannot be parsed."""


class MalformedRecordError(ParsingError):
    """Raised when a record does not conform to expected field structure."""


class BlankRecordError(ParsingError):
    """Raised when a log line is blank or whitespace-only."""


class MissingFieldError(ParsingError):
    """Raised when a required field is missing from a parsed record."""


class CorruptedRecordError(ParsingError):
    """Raised when a log line contains unrecoverable corruption."""


# Validation Errors
class ValidationError(LogProcessingError):
    """Raised when a log record fails validation checks."""


# Pipeline / Storage Errors
class StorageError(LogProcessingError):
    """Raised when output cannot be written to disk."""


class PipelineError(LogProcessingError):
    """Raised when pipeline execution fails unrecoverably."""
