"""Custom exceptions for log processing failures."""

from LogProcessing.exceptions.errors import (
    BlankRecordError,
    CorruptedRecordError,
    EmptyLogFileError,
    IngestionError,
    InputFileNotFoundError,
    InputFileTypeError,
    LogFileTooLargeError,
    LogProcessingError,
    MalformedRecordError,
    MissingFieldError,
    ParsingError,
    PipelineError,
    StorageError,
    UnsupportedLogFileError,
    ValidationError,
)

__all__ = [
    "BlankRecordError",
    "CorruptedRecordError",
    "EmptyLogFileError",
    "IngestionError",
    "InputFileNotFoundError",
    "InputFileTypeError",
    "LogFileTooLargeError",
    "LogProcessingError",
    "MalformedRecordError",
    "MissingFieldError",
    "ParsingError",
    "PipelineError",
    "StorageError",
    "UnsupportedLogFileError",
    "ValidationError",
]
