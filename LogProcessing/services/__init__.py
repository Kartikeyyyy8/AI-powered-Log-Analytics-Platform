"""Pipeline orchestration service package."""

__all__ = ["ProcessingResult", "process_logs"]


def __getattr__(name: str):
    if name in __all__:
        from LogProcessing.services.pipeline import ProcessingResult, process_logs

        exports = {
            "ProcessingResult": ProcessingResult,
            "process_logs": process_logs,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
