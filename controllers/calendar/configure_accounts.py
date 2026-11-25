# SPDX-License-Identifier: MIT
"""Configure calendar accounts without passing passwords on the command line."""

from __future__ import annotations

import argparse
import re
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
    parser.add_argument(
        "action", choices=("list", "add", "enable", "disable", "password", "remove", "status")
    )
    parser.add_argument("--account-id")
    parser.add_argument("--provider", choices=("caldav", "proton"))
    parser.add_argument("--endpoint-default", default="")
    args = parser.parse_args()
    accounts = load_accounts(args.accounts_file)
    if args.action == "list":
        if not accounts:
            print("No calendar accounts configured.")
            return
        for index, account in enumerate(accounts, start=1):
            state = "enabled" if account.enabled else "disabled"
            print(f"{index}. {account.username} ({account.provider}) [{state}]")
        return
    account_id = args.account_id
    if args.action != "add" and account_id is None:
        candidates = tuple(
            account
            for account in accounts
            if (args.action != "enable" or not account.enabled)
            and (args.action != "disable" or account.enabled)
        )
        if not candidates:
            print("No calendar accounts configured." if not accounts else f"All accounts are already {args.action}d.")
            return
        for index, account in enumerate(candidates, start=1):
            state = "enabled" if account.enabled else "disabled"
            print(f"{index}. {account.username} ({account.provider}) [{state}]")
        print("0. Back")
        choice = input("Select account: ").strip()
        if choice == "0":
            return
        if not choice.isascii() or not choice.isdecimal() or len(choice) > 9:
            parser.error("Select a listed account number")
        index = int(choice)
        if not 1 <= index <= len(candidates):
            parser.error("Select a listed account number")
        account_id = candidates[index - 1].account_id
    if args.action == "status":
        selected = next((account for account in accounts if account.account_id == account_id), None)
        if selected is None:
            parser.error("Unknown account ID")
        action = "disable" if selected.enabled else "enable"
        if input(f"{action.capitalize()} {selected.username}? [y/N] ").strip().lower() != "y":
            return
        args.action = action
    if args.action == "add":
        provider = args.provider or input("Provider (caldav/proton): ").strip().lower()
        username = input("Calendar username: ").strip()
        if account_id is None:
            base = re.sub(r"[^a-z0-9_]+", "_", f"{provider}_{username.lower()}")[:55]
            account_id = base
            suffix = 2
            while any(account.account_id == account_id for account in accounts):
                account_id = f"{base}_{suffix}"
                suffix += 1
        if any(account.account_id == account_id for account in accounts):
            parser.error("Account ID already exists")
        default = args.endpoint_default
        if provider == "proton":
            default = default or "http://127.0.0.1:8080/caldav/"
        prompt = f"CalDAV endpoint [{default}]: " if default else "CalDAV endpoint: "
        url = input(prompt).strip() or default
        try:
            account = CalendarAccount(account_id, provider, username, url)
        except ValueError as exc:
            parser.error(str(exc))
        secrets = EnvironmentVariableSecretManager()
        password = None
        if provider == "proton" and url == "http://127.0.0.1:8080/caldav/":
            stored = secrets.get_secret("CARBONATE_BRIDGE_PASSWORD")
            if stored and input("Reuse stored Carbonate bridge password? [Y/n] ").lower() != "n":
                password = stored
        if password is None:
            password = getpass("Calendar password or app password: ")
        if not password.strip():
            parser.error("Password cannot be empty")
        paths = CalendarAccountPaths(args.accounts_file.parent / "calendar-accounts", account)
        paths.catalog.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        probe = create_calendar_provider(
            account,
            paths,
            EnvironmentVariableSecretManager(environment={account.password_secret: password}),
        )
        now = datetime.now(timezone.utc)
        probe.list_events(now, now + timedelta(days=1))
        if not probe.last_sync_status or not any(status.ok for status in probe.last_sync_status):
            parser.error("No calendar could be read; account was not saved")
        secrets.set_secret(account.password_secret, password)
        save_accounts(args.accounts_file, (*accounts, account))
    elif args.action in ("password", "remove"):
        existing = next((account for account in accounts if account.account_id == account_id), None)
        if existing is None:
            parser.error("Unknown account ID")
        if args.action == "remove":
            if input(f"Remove {account_id} from configuration? [y/N] ").lower() != "y":
                return
            save_accounts(
                args.accounts_file,
                tuple(account for account in accounts if account.account_id != account_id),
            )
            print("Account removed from configuration; cached data and secret retained.")
        else:
            password = getpass("New calendar password or app password: ")
            paths = CalendarAccountPaths(args.accounts_file.parent / "calendar-accounts", existing)
            paths.catalog.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            probe = create_calendar_provider(
                existing,
                paths,
                EnvironmentVariableSecretManager(environment={existing.password_secret: password}),
            )
            now = datetime.now(timezone.utc)
            probe.list_events(now, now + timedelta(days=1))
            if not any(status.ok and not status.disabled for status in probe.last_sync_status):
                parser.error("Credential validation failed; existing password retained")
            EnvironmentVariableSecretManager().set_secret(existing.password_secret, password)
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
