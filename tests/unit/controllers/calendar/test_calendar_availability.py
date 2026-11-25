# SPDX-License-Identifier: MIT
"""Verify empty calendar presentation does not imply successful synchronization."""

from ui.calendar.calendar_models import CalendarHealthView


def test_initial_calendar_has_no_confirmed_sync():
    assert CalendarHealthView().empty_message == "No confirmed calendar sync yet."


def test_failed_initial_sync_is_not_an_empty_calendar():
    health = CalendarHealthView(status="failed")
    assert health.empty_message == "Calendar sync failed; no confirmed data."


def test_successful_empty_cache_is_distinct_from_initial_state():
    health = CalendarHealthView(status="ok", last_data_refresh_age_seconds=0.0)
    assert health.empty_message == "No cached appointments."


def test_failed_refresh_preserves_cached_result_semantics():
    health = CalendarHealthView(status="failed", stale=True, last_data_refresh_age_seconds=3600.0)
    assert health.empty_message == "No cached appointments."
