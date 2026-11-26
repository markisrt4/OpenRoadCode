# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only calendar sync diagnostics; never print event contents."""

from __future__ import annotations

import argparse
import getpass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from controllers.calendar.caldav_adapter import CalDavAdapter
from controllers.calendar.caldav_provider import CalDavCalendarProvider
from controllers.calendar.calendar_selection import (
    load_disabled_calendar_ids,
    save_disabled_calendar_ids,
)
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080/caldav/")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password-secret", default="CALDAV_BRIDGE_PASSWORD")
    parser.add_argument("--prompt-password", action="store_true")
    parser.add_argument(
        "--selection-file",
        type=Path,
        default=Path.home() / ".config/openroadcode/calendar-selection.json",
    )
    parser.add_argument("--disable-index", type=int)
    parser.add_argument("--enable-index", type=int)
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()
    if args.days < 1 or args.days > 31 or args.timeout <= 0:
        parser.error("days must be 1..31 and timeout must be positive")
    if args.disable_index is not None and args.enable_index is not None:
        parser.error("Choose only one of --disable-index and --enable-index")
    secrets = (
        EnvironmentVariableSecretManager(
            environment={args.password_secret: getpass.getpass("Bridge password: ")}
        )
        if args.prompt_password
        else EnvironmentVariableSecretManager()
    )
    adapter = CalDavAdapter(args.url, args.username, secrets, args.password_secret, args.timeout)
    calendars = adapter.discover_calendars()
    disabled = set(load_disabled_calendar_ids(args.selection_file))
    for index, calendar in enumerate(calendars, 1):
        print(
            f"{index}. {calendar.display_name} [{'disabled' if calendar.href in disabled else 'enabled'}]"
        )
    choice = args.disable_index if args.disable_index is not None else args.enable_index
    if choice is not None:
        if not 1 <= choice <= len(calendars):
            parser.error("calendar index outside discovered range")
        calendar_id = calendars[choice - 1].href
        if args.disable_index is not None:
            disabled.add(calendar_id)
        else:
            disabled.discard(calendar_id)
        save_disabled_calendar_ids(args.selection_file, disabled)
        print("Calendar selection saved")
        return
    provider = CalDavCalendarProvider("caldav", adapter, disabled)
    start = datetime.now(timezone.utc)
    events = provider.list_events(start, start + timedelta(days=args.days))
    print(f"Normalized events: {len(events)}")
    for index, status in enumerate(provider.last_sync_status, 1):
        state = "disabled" if status.disabled else "ok" if status.ok else "failed"
        print(
            f"Calendar {index}: {state}, resources={status.resource_count}, "
            f"events={status.event_count}, skipped={status.skipped_resources}"
            + (f", error={status.error}" if status.error else "")
        )


if __name__ == "__main__":
    main()
