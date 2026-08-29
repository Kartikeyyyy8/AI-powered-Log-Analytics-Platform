"""Log storage package."""

from LogProcessing.storage.dead_letter import DeadLetterWriter
from LogProcessing.storage.writer import JsonLinesWriter, write_json_report

__all__ = ["DeadLetterWriter", "JsonLinesWriter", "write_json_report"]
