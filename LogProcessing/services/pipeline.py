"""End-to-end log processing pipeline service."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from LogProcessing.cleaning.cleaner import LogCleaner
from LogProcessing.config.settings import DEFAULT_SETTINGS
from LogProcessing.exceptions.errors import ParsingError, ValidationError
from LogProcessing.ingestion.file_ingestor import FileIngestor
from LogProcessing.normalization.normalizer import LogNormalizer
from LogProcessing.parsing.healthapp_parser import HealthAppParser
from LogProcessing.profiling.dataset_profiler import profile_dataset, write_profile
from LogProcessing.quality.analyzer import QualityAnalyzer
from LogProcessing.schemas.dead_letter_log import DeadLetterLogRecord
from LogProcessing.storage.dead_letter import DeadLetterWriter
from LogProcessing.storage.writer import JsonLinesWriter, write_json_report
from LogProcessing.validation.validator import LogValidator


@dataclass(frozen=True)
class ProcessingResult:
    """Summary of pipeline execution result and output paths."""

    processed_logs_path: Path
    dead_letter_logs_path: Path
    quality_report_path: Path
    dataset_profile_path: Path | None
    total_records: int
    valid_records: int
    invalid_records: int


def process_logs(
    input_path: str | Path,
    output_dir: str | Path = "outputs",
    generate_profile: bool = True,
) -> ProcessingResult:
    """Execute the end-to-end log processing pipeline.

    Streams raw lines, parses, cleans, normalizes, validates, tracks quality,
    and writes ML-ready JSONL files along with data quality reports.

    Args:
        input_path: Path to the raw log file (e.g. HealthApp.log).
        output_dir: Directory where output JSONL and report JSON files will be written.
        generate_profile: Whether to also run/update dataset profiling report.

    Returns:
        ProcessingResult with paths and summary counts.
    """
    input_file = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    processed_logs_path = out_dir / DEFAULT_SETTINGS.default_processed_filename
    dead_letter_logs_path = out_dir / DEFAULT_SETTINGS.default_dead_letter_filename
    quality_report_path = out_dir / DEFAULT_SETTINGS.default_quality_report_filename
    dataset_profile_path = (
        (out_dir / DEFAULT_SETTINGS.default_dataset_profile_filename)
        if generate_profile
        else None
    )

    ingestor = FileIngestor()
    parser = HealthAppParser()
    validator = LogValidator()
    analyzer = QualityAnalyzer()

    total_lines = 0

    with JsonLinesWriter(processed_logs_path) as processed_writer, DeadLetterWriter(
        dead_letter_logs_path
    ) as dead_letter_writer:
        for raw_record in ingestor.ingest_file(input_file):
            total_lines += 1

            # 1. Parsing
            try:
                parsed_record = parser.parse(raw_record)
            except (ParsingError, Exception) as exc:
                dead_letter = DeadLetterLogRecord(
                    source=raw_record.source_name,
                    line_number=raw_record.line_number,
                    raw_message=raw_record.raw_message,
                    error_reason=f"parsing_failed: {exc}",
                    ingestion_timestamp=raw_record.ingestion_timestamp,
                    quality_flags=["parsing_failed"],
                    metadata={"exception_type": type(exc).__name__},
                )
                dead_letter_writer.write(dead_letter)
                analyzer.record_dead_letter(dead_letter)
                continue

            # 2. Cleaning
            cleaned_record = LogCleaner.clean_record(parsed_record)

            # 3. Normalization & Classification
            structured_record = LogNormalizer.normalize(cleaned_record)

            # 4. Validation
            is_valid, validation_errors = validator.validate(structured_record)
            if not is_valid:
                dead_letter = DeadLetterLogRecord(
                    source=structured_record.source,
                    line_number=structured_record.line_number,
                    raw_message=structured_record.raw_message,
                    error_reason="; ".join(validation_errors),
                    ingestion_timestamp=structured_record.ingestion_timestamp,
                    quality_flags=structured_record.quality_flags + ["validation_failed"],
                    metadata={"validation_errors": validation_errors},
                )
                dead_letter_writer.write(dead_letter)
                analyzer.record_dead_letter(dead_letter)
                continue

            # 5. Valid Structured Record
            processed_writer.write(structured_record)
            analyzer.record_processed_record(structured_record)

    # Compile and write Quality Report
    report = analyzer.generate_report(total_lines=total_lines)
    write_json_report(report.to_dict(), quality_report_path)

    # Optionally run dataset profiling
    if generate_profile and dataset_profile_path is not None:
        profile = profile_dataset(input_file)
        write_profile(profile, dataset_profile_path)

    return ProcessingResult(
        processed_logs_path=processed_logs_path,
        dead_letter_logs_path=dead_letter_logs_path,
        quality_report_path=quality_report_path,
        dataset_profile_path=dataset_profile_path,
        total_records=total_lines,
        valid_records=report.valid_records,
        invalid_records=report.invalid_records,
    )


def main() -> int:
    arg_parser = argparse.ArgumentParser(
        description="Run the AI Log Analytics Log Processing pipeline."
    )
    arg_parser.add_argument("input_path", help="Path to raw log file (e.g. HealthApp.log)")
    arg_parser.add_argument(
        "--output-dir",
        "-o",
        default="LogProcessing/outputs",
        help="Directory to save processed outputs (default: LogProcessing/outputs)",
    )
    arg_parser.add_argument(
        "--no-profile",
        action="store_true",
        help="Skip generating dataset_profile.json",
    )
    args = arg_parser.parse_args()

    result = process_logs(
        input_path=args.input_path,
        output_dir=args.output_dir,
        generate_profile=not args.no_profile,
    )

    print("=" * 60)
    print("LOG PROCESSING PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Total lines read:      {result.total_records:,}")
    print(f"Valid records saved:   {result.valid_records:,}")
    print(f"Dead letter records:   {result.invalid_records:,}")
    print(f"Processed logs:        {result.processed_logs_path}")
    print(f"Dead letter logs:      {result.dead_letter_logs_path}")
    print(f"Quality report:        {result.quality_report_path}")
    if result.dataset_profile_path:
        print(f"Dataset profile:       {result.dataset_profile_path}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
