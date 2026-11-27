# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Persistent calendar synchronization health for local consumers."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from .calendar_sync_worker import CalendarSyncResult


class CalendarSyncHealth:
    """Publish atomic health snapshots without event or account details."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> dict:
        """Read the latest snapshot, or an empty state if unavailable."""
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def mark_started(self, attempted_at: datetime, interval: float) -> None:
        """Publish an attempt in progress while retaining prior refresh metadata."""
        snapshot = self.read()
        snapshot.update(
            last_attempt=attempted_at.isoformat(),
            interval_seconds=interval,
            syncing=True,
        )
        self._write(snapshot)

    def record(
        self,
        attempted_at: datetime,
        completed_at: datetime,
        elapsed: float,
        interval: float,
        result: CalendarSyncResult | None,
    ) -> None:
        """Record an attempt and preserve the last complete successful result."""
        previous = self.read()
        snapshot = {
            "version": 1,
            "syncing": False,
            "last_attempt": attempted_at.isoformat(),
            "last_completed": completed_at.isoformat(),
            "interval_seconds": interval,
            "duration_seconds": round(elapsed, 3),
            "last_data_refresh": previous.get("last_data_refresh", previous.get("last_success")),
            "last_success": previous.get("last_success"),
            "last_success_metrics": previous.get("last_success_metrics"),
            "metrics": None,
            "status": "failed",
        }
        if result is not None:
            metrics = {
                "cached_calendars": result.cached_calendars,
                "failed_calendars": sum(not s.ok and not s.disabled for s in result.statuses),
                "disabled_calendars": sum(s.disabled for s in result.statuses),
                "synced_events": sum(s.event_count for s in result.statuses if s.ok),
                "skipped_resources": sum(s.skipped_resources for s in result.statuses),
            }
            snapshot["metrics"] = metrics
            if result.cached_calendars > 0:
                snapshot["last_data_refresh"] = completed_at.isoformat()
            if metrics["failed_calendars"] or metrics["skipped_resources"]:
                snapshot["status"] = "degraded"
            else:
                snapshot["status"] = "ok"
                snapshot["last_success"] = completed_at.isoformat()
                snapshot["last_success_metrics"] = metrics
        self._write(snapshot)

    def _write(self, snapshot: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(snapshot, stream)
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
