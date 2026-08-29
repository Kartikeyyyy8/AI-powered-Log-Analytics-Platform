"""Message classification and metric extraction for HealthApp logs."""

from __future__ import annotations

import re
from typing import Any

# Regex patterns for extracting specific metrics from common message templates
RE_STAND_STEP = re.compile(r"^onStandStepChanged\s+(\d+)$")
RE_ON_EXTEND = re.compile(r"^onExtend:(\d+)(?:\s+(\d+))?(?:\s+(\d+))?(?:\s+(\d+))?")
RE_CALORIES = re.compile(r"calculateCaloriesWithCache\s+totalCalories=(\d+(?:\.\d+)?)")
RE_ALTITUDE = re.compile(r"calculateAltitudeWithCache\s+totalAltitude=(-?\d+(?:\.\d+)?)")
RE_REPORT = re.compile(r"REPORT\s*:\s*(\d+)(?:\s+(\d+))?(?:\s+(\d+))?(?:\s+(\d+))?")
RE_RELOAD_STEPS = re.compile(r"tryToReloadTodayBasicSteps(\d+)(?:\|(\d+))?(?:\|(\d+))?(?:\|(\d+))?")
RE_HEALTH_NOTIFICATION = re.compile(r"upDateHealthNotification\(\)(?:\|(\d+(?:\.\d+)?))?(?:\|(\d+(?:\.\d+)?))?(?:\|(\d+(?:\.\d+)?))?")
RE_STAT_DATA = re.compile(r"saveStatData\(\)\s*type\s*=\s*(\d+),\s*time\s*=\s*(\d+)")
RE_UPLOAD_MINUTE = re.compile(r"upLoadOneMinuteDataToEngine\s*time\s*=\s*(\d+)")
RE_GENERAL_NUMBERS = re.compile(r"\b(\d+(?:\.\d+)?)\b")


class MessageClassifier:
    """Classifies log messages into semantic types and extracts relevant metrics."""

    @staticmethod
    def classify_and_extract(message: str) -> tuple[str, dict[str, Any]]:
        """Classify message text and extract numeric/domain metrics.

        Returns:
            Tuple of (parsed_message_type, extracted_metrics).
        """
        stripped = message.strip()
        if not stripped:
            return "EMPTY_MESSAGE", {}

        metrics: dict[str, Any] = {}

        # 1. onStandStepChanged
        m_step = RE_STAND_STEP.match(stripped)
        if m_step:
            metrics["step_count"] = int(m_step.group(1))
            return "onStandStepChanged", metrics

        # 2. onExtend
        m_ext = RE_ON_EXTEND.match(stripped)
        if m_ext:
            if m_ext.group(1):
                metrics["timestamp_ms"] = int(m_ext.group(1))
            for idx, g in enumerate(m_ext.groups()[1:], start=1):
                if g is not None:
                    metrics[f"param_{idx}"] = int(g)
            return "onExtend", metrics

        # 3. calculateCaloriesWithCache
        m_cal = RE_CALORIES.search(stripped)
        if m_cal:
            val = float(m_cal.group(1))
            metrics["total_calories"] = int(val) if val.is_integer() else val
            return "calculateCaloriesWithCache", metrics

        # 4. calculateAltitudeWithCache
        m_alt = RE_ALTITUDE.search(stripped)
        if m_alt:
            val = float(m_alt.group(1))
            metrics["total_altitude"] = int(val) if val.is_integer() else val
            return "calculateAltitudeWithCache", metrics

        # 5. REPORT
        if "REPORT" in stripped:
            m_rep = RE_REPORT.search(stripped)
            if m_rep:
                if m_rep.group(1):
                    metrics["timestamp_ms"] = int(m_rep.group(1))
                for idx, g in enumerate(m_rep.groups()[1:], start=1):
                    if g is not None:
                        metrics[f"v_{idx}"] = int(g)
            return "REPORT", metrics

        # 6. tryToReloadTodayBasicSteps
        if "tryToReloadTodayBasicSteps" in stripped:
            m_reload = RE_RELOAD_STEPS.search(stripped)
            if m_reload:
                if m_reload.group(1):
                    metrics["timestamp_ms"] = int(m_reload.group(1))
                if m_reload.group(2):
                    metrics["step_count"] = int(m_reload.group(2))
            return "tryToReloadTodayBasicSteps", metrics

        # 7. upDateHealthNotification
        if "upDateHealthNotification" in stripped:
            m_notif = RE_HEALTH_NOTIFICATION.search(stripped)
            if m_notif:
                if m_notif.group(1):
                    metrics["metric_1"] = float(m_notif.group(1))
                if m_notif.group(2):
                    metrics["metric_2"] = float(m_notif.group(2))
                if m_notif.group(3):
                    metrics["metric_3"] = float(m_notif.group(3))
            return "upDateHealthNotification", metrics

        # 8. Step details
        if stripped.startswith("getTodayTotalDetailSteps"):
            return "getTodayTotalDetailSteps", metrics

        if stripped.startswith("setTodayTotalDetailSteps"):
            return "setTodayTotalDetailSteps", metrics

        # 9. Broadcast and system events
        if "SCREEN_ON" in stripped:
            return "SCREEN_ON", metrics

        if "SCREEN_OFF" in stripped:
            return "SCREEN_OFF", metrics

        if "TIME_TICK" in stripped:
            return "TIME_TICK", metrics

        if "BOOT_COMPLETED" in stripped:
            return "BOOT_COMPLETED", metrics

        if "FAILED_ERROR_DATA" in stripped:
            return "FAILED_ERROR_DATA", metrics

        if "flush sensor data" in stripped:
            return "flush_sensor_data", metrics

        if "saveStatData" in stripped:
            m_stat = RE_STAT_DATA.search(stripped)
            if m_stat:
                metrics["type"] = int(m_stat.group(1))
                metrics["time"] = int(m_stat.group(2))
            return "saveStatData", metrics

        if "upLoadOneMinuteDataToEngine" in stripped:
            m_up = RE_UPLOAD_MINUTE.search(stripped)
            if m_up:
                metrics["time"] = int(m_up.group(1))
            return "upLoadOneMinuteDataToEngine", metrics

        # 10. Fallback: extract primary keyword / prefix
        prefix = re.split(r"[\s=:|(]", stripped, maxsplit=1)[0]
        msg_type = prefix if prefix else "UNKNOWN"
        return msg_type, metrics
