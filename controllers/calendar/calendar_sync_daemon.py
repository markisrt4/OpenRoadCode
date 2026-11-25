# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Run periodic CalDAV-to-SQLite synchronization without exposing event contents."""

from __future__ import annotations

import argparse
import logging
import signal
import threading
from math import isfinite
from pathlib import Path

from controllers.calendar.caldav_adapter import CalDavAdapter
from controllers.calendar.caldav_provider import CalDavCalendarProvider
from controllers.calendar.calendar_event_cache import CalendarEventCache
from controllers.calendar.calendar_selection import (
    load_disabled_calendar_ids,
    save_calendar_catalog,
)
from controllers.calendar.calendar_sync_health import CalendarSyncHealth
from controllers.calendar.calendar_sync_scheduler import CalendarSyncScheduler
from controllers.calendar.calendar_sync_worker import CalendarSyncWorker
from controllers.calendar.multi_account_sync import run_accounts
from controllers.connectivity.online_mode import saved_online_mode
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080/caldav/")
    parser.add_argument("--username")
    parser.add_argument("--accounts-file", type=Path)
    parser.add_argument("--metadata-root", type=Path)
    parser.add_argument("--account-id", default="caldav")
    parser.add_argument("--password-secret", default="CALDAV_BRIDGE_PASSWORD")
    parser.add_argument(
        "--selection-file",
        type=Path,
        default=Path.home() / ".config/openroadcode/calendar-selection.json",
    )
    parser.add_argument(
        "--cache-file",
        type=Path,
        default=Path.home() / ".local/share/openroadcode/calendar/events.sqlite3",
    )
    parser.add_argument("--interval-seconds", type=float, default=900)
    parser.add_argument("--past-days", type=int, default=7)
    parser.add_argument("--future-days", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if args.accounts_file is None and (
        not args.username or not args.username.strip() or not args.account_id.strip()
    ):
        parser.error("username and account-id must be nonempty")
    if not isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be positive")
    if (
        not isfinite(args.interval_seconds)
        or args.interval_seconds <= 0
        or args.past_days < 0
        or args.future_days <= 0
    ):
        parser.error("invalid synchronization interval or window")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.accounts_file is not None:
        if args.username is not None:
            parser.error("--username and --accounts-file are mutually exclusive")
        stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda _signum, _frame: stop.set())
        signal.signal(signal.SIGINT, lambda _signum, _frame: stop.set())
        run_accounts(
            args.accounts_file,
            args.metadata_root or args.accounts_file.parent / "calendar-accounts",
            args.cache_file,
            stop,
            interval_seconds=args.interval_seconds,
            past_days=args.past_days,
            future_days=args.future_days,
            timeout_seconds=args.timeout,
        )
        return
    adapter = CalDavAdapter(
        args.url,
        args.username,
        EnvironmentVariableSecretManager(),
        args.password_secret,
        timeout_seconds=args.timeout,
    )
    provider = CalDavCalendarProvider(
        args.account_id,
        adapter,
        selection_loader=lambda: load_disabled_calendar_ids(args.selection_file),
        discovery_listener=lambda calendars: save_calendar_catalog(
            args.cache_file.with_suffix(".catalog.json"),
            {calendar.href: calendar.display_name for calendar in calendars},
        ),
    )
    worker = CalendarSyncWorker(args.account_id, provider, CalendarEventCache(args.cache_file))
    scheduler = CalendarSyncScheduler(
        worker,
        interval_seconds=args.interval_seconds,
        past_days=args.past_days,
        future_days=args.future_days,
        online_allowed=saved_online_mode,
        health=CalendarSyncHealth(args.cache_file.with_suffix(".health.json")),
    )
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda _signum, _frame: stop.set())
    signal.signal(signal.SIGINT, lambda _signum, _frame: stop.set())
    scheduler.run(stop)


if __name__ == "__main__":
    main()
