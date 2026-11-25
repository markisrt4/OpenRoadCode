# SPDX-License-Identifier: MIT
"""Run independent synchronization schedules for configured accounts."""

from __future__ import annotations

import threading
from pathlib import Path

from controllers.connectivity.online_mode import saved_online_mode
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager

from .calendar_accounts import load_accounts
from .calendar_event_cache import CalendarEventCache
from .calendar_provider_factory import CalendarAccountPaths, create_calendar_provider
from .calendar_sync_health import CalendarSyncHealth
from .calendar_sync_scheduler import CalendarSyncScheduler
from .calendar_sync_worker import CalendarSyncWorker


def run_accounts(
    accounts_file: Path,
    metadata_root: Path,
    cache_file: Path,
    stop: threading.Event,
    *,
    interval_seconds: float = 900,
    past_days: int = 7,
    future_days: int = 30,
    timeout_seconds: float = 30,
) -> None:
    """Run enabled accounts independently until shutdown."""
    accounts = load_accounts(accounts_file)
    cache = CalendarEventCache(cache_file)
    secrets = EnvironmentVariableSecretManager()
    schedulers = []
    for account in accounts:
        if not account.enabled:
            continue
        paths = CalendarAccountPaths(metadata_root, account)
        paths.health.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        provider = create_calendar_provider(
            account, paths, secrets, timeout_seconds=timeout_seconds
        )
        schedulers.append(
            CalendarSyncScheduler(
                CalendarSyncWorker(account.account_id, provider, cache),
                interval_seconds=interval_seconds,
                past_days=past_days,
                future_days=future_days,
                online_allowed=saved_online_mode,
                health=CalendarSyncHealth(paths.health),
            )
        )
    threads: list[threading.Thread] = []
    try:
        for scheduler in schedulers:
            thread = threading.Thread(target=scheduler.run, args=(stop,))
            thread.start()
            threads.append(thread)
        stop.wait()
    finally:
        stop.set()
        for thread in threads:
            thread.join()
