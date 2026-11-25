# SPDX-License-Identifier: MIT
"""Construct calendar providers without exposing credentials to consumers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from security.secret_manager_if import SecretManagerIf

from .caldav_adapter import CalDavAdapter
from .caldav_provider import CalDavCalendarProvider
from .calendar_accounts import CalendarAccount
from .calendar_selection import load_disabled_calendar_ids, save_calendar_catalog


@dataclass(frozen=True)
class CalendarAccountPaths:
    """Independent metadata paths for a configured account."""

    root: Path
    account: CalendarAccount

    @property
    def selection(self) -> Path:
        return self.root / self.account.account_id / "selection.json"

    @property
    def catalog(self) -> Path:
        return self.root / self.account.account_id / "catalog.json"

    @property
    def health(self) -> Path:
        return self.root / self.account.account_id / "health.json"


def create_calendar_provider(
    account: CalendarAccount,
    paths: CalendarAccountPaths,
    secrets: SecretManagerIf,
    *,
    timeout_seconds: float = 30,
) -> CalDavCalendarProvider:
    """Build the read-only provider for a configured CalDAV or Proton account."""
    if paths.account != account:
        raise ValueError("Calendar metadata paths must belong to the account")
    adapter = CalDavAdapter(
        account.url,
        account.username,
        secrets,
        account.password_secret,
        timeout_seconds=timeout_seconds,
    )
    return CalDavCalendarProvider(
        account.account_id,
        adapter,
        selection_loader=lambda: load_disabled_calendar_ids(paths.selection),
        discovery_listener=lambda calendars: save_calendar_catalog(
            paths.catalog,
            {calendar.href: calendar.display_name for calendar in calendars},
        ),
    )
