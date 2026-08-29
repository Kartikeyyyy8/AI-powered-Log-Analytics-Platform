"""Pipeline orchestration service package."""

from LogProcessing.services.pipeline import ProcessingResult, process_logs

__all__ = ["ProcessingResult", "process_logs"]
