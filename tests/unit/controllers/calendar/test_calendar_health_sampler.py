# SPDX-License-Identifier: MIT
"""Regression tests for calendar diagnostics."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from controllers.system.calendar_health_sampler import sample_calendar_health


@pytest.mark.parametrize(
    ("status", "age", "stale"),
    [("ok", 60, False), ("ok", 1801, True), ("degraded", 60, False), ("failed", 60, False)],
)
def test_health_status(tmp_path, status, age, stale):
    now = datetime(2026, 11, 24, tzinfo=timezone.utc)
    completed = (now - timedelta(seconds=age)).isoformat()
    path = tmp_path / "health.json"
    path.write_text(
        json.dumps(
            {
                "status": status,
                "last_completed": completed,
                "last_success": completed,
                "interval_seconds": 900,
                "duration_seconds": 2,
                "metrics": {"synced_events": 45},
            }
        )
    )
    health = sample_calendar_health(path, now)
    assert health["status"] == status
    assert health["stale"] is stale
    assert health["last_success_age_seconds"] == age
    assert health["metrics"]["synced_events"] == 45


@pytest.mark.parametrize("content", [None, "{", "[]", "{}", '{"status":"ok"}'])
def test_unavailable_health(tmp_path, content):
    path = tmp_path / "health.json"
    if content is not None:
        path.write_text(content)
    assert sample_calendar_health(path) == {"status": "unavailable"}
