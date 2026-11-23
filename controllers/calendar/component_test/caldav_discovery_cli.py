# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Discover live CalDAV calendars without printing private event data."""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime, timedelta, timezone

from controllers.calendar.caldav_adapter import (
    CalDavAdapter,
    CalDavAuthenticationError,
    CalDavHttpError,
)
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080/caldav/")
    parser.add_argument("--username", required=True)
    parser.add_argument(
        "--password-secret",
        default="CALDAV_BRIDGE_PASSWORD",
        help="Name of the secret in ORC's existing secrets configuration",
    )
    parser.add_argument(
        "--prompt-password",
        action="store_true",
        help="Prompt interactively instead of reading ORC secrets",
    )
    parser.add_argument("--query-days", type=int, default=0, help="Read-only event query window in days (0 disables)")
    args = parser.parse_args()
    if args.query_days < 0 or args.query_days > 31:
        parser.error("--query-days must be between 0 and 31")
    secrets = (
        EnvironmentVariableSecretManager(
            environment={args.password_secret: getpass.getpass("CalDAV bridge password: ")}
        )
        if args.prompt_password
        else EnvironmentVariableSecretManager()
    )
    adapter = CalDavAdapter(args.url, args.username, secrets, args.password_secret)
    try:
        calendars = adapter.discover_calendars()
    except CalDavAuthenticationError as error:
        print(f"Authentication error: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    except CalDavHttpError as error:
        print(f"CalDAV server error: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    print(f"Discovered {len(calendars)} calendar(s)")
    for calendar in calendars:
        print(f"  {calendar.display_name}")
    if args.query_days:
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=args.query_days)
        for index, calendar in enumerate(calendars, start=1):
            try:
                resources = adapter.query_event_resources(calendar, start, end)
            except (CalDavAuthenticationError, CalDavHttpError) as error:
                print(f"Calendar {index}: {error}", file=sys.stderr)
                raise SystemExit(1) from None
            print(f"Calendar {index}: {len(resources)} iCalendar resource(s) in query window")


if __name__ == "__main__":
    main()
