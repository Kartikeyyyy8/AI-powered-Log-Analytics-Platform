"""Configuration and default settings for LogProcessing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogProcessingSettings:
    """Settings controlling ingestion, cleaning, validation, and storage."""

    default_encoding: str = "utf-8"
    supported_extensions: tuple[str, ...] = (".log", ".txt", ".jsonl")
    max_file_size_bytes: int = 512 * 1024 * 1024  # 512MB

    # Defaults for storage outputs
    default_processed_filename: str = "processed_logs.jsonl"
    default_dead_letter_filename: str = "dead_letter_logs.jsonl"
    default_quality_report_filename: str = "quality_report.json"
    default_dataset_profile_filename: str = "dataset_profile.json"


DEFAULT_SETTINGS = LogProcessingSettings()
