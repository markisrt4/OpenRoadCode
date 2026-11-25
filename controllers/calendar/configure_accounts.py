# SPDX-License-Identifier: MIT
"""Configure calendar accounts without passing passwords on the command line."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path

from security.environment_variable_secret_manager import EnvironmentVariableSecretManager

from .calendar_accounts import CalendarAccount, load_accounts, save_accounts
from .calendar_provider_factory import CalendarAccountPaths, create_calendar_provider


def main() -> None:
    """Manage persistent account configuration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--accounts-file",
        type=Path,
        default=Path.home() / ".config/openroadcode/calendar-accounts.json",
    )
    parser.add_argument("action", choices=("list", "add", "enable", "disable"))
    parser.add_argument("--account-id")
    parser.add_argument("--provider", choices=("caldav", "proton"))
    args = parser.parse_args()
    accounts = load_accounts(args.accounts_file)
    if args.action == "list":
        for account in accounts:
            print(
                account.account_id, account.provider, "enabled" if account.enabled else "disabled"
            )
        return
    account_id = args.account_id or input("Account ID: ").strip()
    if args.action == "add":
        if any(account.account_id == account_id for account in accounts):
            parser.error("Account ID already exists")
        provider = args.provider or input("Provider (caldav/proton): ").strip().lower()
        username = input("Calendar username: ").strip()
        url = input("CalDAV endpoint: ").strip()
        if provider == "proton" and not url:
            url = "http://127.0.0.1:8080/caldav/"
        account = CalendarAccount(account_id, provider, username, url)
        secrets = EnvironmentVariableSecretManager(
            secrets_file=args.accounts_file.parent / "secrets.env"
        )
        password = getpass("Calendar password or app password: ")
        if not password.strip():
            parser.error("Password cannot be empty")
        probe = create_calendar_provider(
            account,
            CalendarAccountPaths(args.accounts_file.parent / "calendar-accounts", account),
            EnvironmentVariableSecretManager(environment={account.password_secret: password}),
        )
        now = datetime.now(timezone.utc)
        probe.list_events(now, now + timedelta(days=1))
        if not probe.last_sync_status or not any(status.ok for status in probe.last_sync_status):
            parser.error("No calendar could be read; account was not saved")
        secrets.set_secret(account.password_secret, password)
        save_accounts(args.accounts_file, (*accounts, account))
    else:
        if not any(account.account_id == account_id for account in accounts):
            parser.error("Unknown account ID")
        save_accounts(
            args.accounts_file,
            tuple(
                replace(account, enabled=args.action == "enable")
                if account.account_id == account_id
                else account
                for account in accounts
            ),
        )
    print("Configuration saved. Restart the calendar synchronization service.")


if __name__ == "__main__":
    main()
