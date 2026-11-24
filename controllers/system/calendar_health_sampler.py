# SPDX-License-Identifier: MIT
"""Read local calendar health without contacting the provider."""

import json
import math
from datetime import datetime, timezone
from pathlib import Path


def sample_calendar_health(path: Path | None = None, now: datetime | None = None) -> dict:
    path = path or Path.home() / ".local/share/openroadcode/calendar/events.health.json"
    now = now or datetime.now(timezone.utc)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        status = raw["status"]
        interval = float(raw["interval_seconds"])
        completed = datetime.fromisoformat(raw["last_completed"])
        age = (now - completed).total_seconds()
        if status not in ("ok", "degraded", "failed") or not math.isfinite(interval):
            raise ValueError("Invalid health")
        if interval <= 0 or age < 0:
            raise ValueError("Invalid timing")
        success = raw.get("last_success")
        success_age = (now - datetime.fromisoformat(success)).total_seconds() if success else None
        if success_age is not None and success_age < 0:
            raise ValueError("Invalid success time")
        metrics = raw.get("metrics") or {}
        return {
            "status": status,
            "stale": age > 2 * interval or (success_age is not None and success_age > 2 * interval),
            "last_success_age_seconds": success_age,
            "last_completed_age_seconds": age,
            "interval_seconds": interval,
            "duration_seconds": float(raw["duration_seconds"]),
            "metrics": {
                key: value
                for key in (
                    "cached_calendars",
                    "failed_calendars",
                    "disabled_calendars",
                    "synced_events",
                    "skipped_resources",
                )
                if type(value := metrics.get(key)) is int and value >= 0
            },
        }
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return {"status": "unavailable"}
