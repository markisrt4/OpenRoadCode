# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Run periodic synchronization for configured calendar accounts."""

from __future__ import annotations

import argparse
import logging
import signal
import threading
from math import isfinite
from pathlib import Path

from controllers.calendar.multi_account_sync import run_accounts


def main() -> None:
    """Run account synchronization until the process receives a stop signal."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--accounts-file",
        type=Path,
        default=Path.home() / ".config/openroadcode/calendar-accounts.json",
    )
    parser.add_argument("--metadata-root", type=Path)
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


if __name__ == "__main__":
    main()
