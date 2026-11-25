# SPDX-License-Identifier: MIT
"""Migrate the default legacy calendar account without deleting its data."""

from __future__ import annotations

import argparse
from pathlib import Path
from shutil import copyfile

from security.environment_variable_secret_manager import EnvironmentVariableSecretManager

from .calendar_accounts import CalendarAccount, save_accounts
from .calendar_provider_factory import CalendarAccountPaths


def main() -> None:
    """Preserve legacy account identity and metadata during migration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--provider", choices=("proton", "caldav"), default="proton")
    parser.add_argument("--url", default="http://127.0.0.1:8080/caldav/")
    args = parser.parse_args()
    config = Path.home() / ".config/openroadcode"
    accounts_file = config / "calendar-accounts.json"
    if accounts_file.exists():
        parser.error("Account configuration already exists; migration will not overwrite it")
    account = CalendarAccount("caldav", args.provider, args.username, args.url)
    secrets = EnvironmentVariableSecretManager()
    password = secrets.get_secret("CALDAV_BRIDGE_PASSWORD")
    if password is None:
        parser.error("Legacy calendar password not found")
    paths = CalendarAccountPaths(config / "calendar-accounts", account)
    cache = Path.home() / ".local/share/openroadcode/calendar/events.sqlite3"
    paths.selection.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    for source, destination in (
        (config / "calendar-selection.json", paths.selection),
        (cache.with_suffix(".catalog.json"), paths.catalog),
        (cache.with_suffix(".health.json"), paths.health),
    ):
        if source.exists() and not destination.exists():
            copyfile(source, destination)
            destination.chmod(0o600)
    secrets.set_secret(account.password_secret, password)
    save_accounts(accounts_file, (account,))
    print("Migration complete. Legacy files and event cache retained.")
    print("Install the multi-account synchronization service before restarting it.")


if __name__ == "__main__":
    main()
