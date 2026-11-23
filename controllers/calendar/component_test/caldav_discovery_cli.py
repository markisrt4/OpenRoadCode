# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Discover live CalDAV calendars without printing private event data."""

from __future__ import annotations

import argparse
import getpass

from controllers.calendar.caldav_adapter import CalDavAdapter
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
    args = parser.parse_args()
    secrets = (
        EnvironmentVariableSecretManager(
            environment={args.password_secret: getpass.getpass("CalDAV bridge password: ")}
        )
        if args.prompt_password
        else EnvironmentVariableSecretManager()
    )
    adapter = CalDavAdapter(args.url, args.username, secrets, args.password_secret)
    calendars = adapter.discover_calendars()
    print(f"Discovered {len(calendars)} calendar(s)")
    for calendar in calendars:
        print(f"  {calendar.display_name}")


if __name__ == "__main__":
    main()
