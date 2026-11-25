# SPDX-License-Identifier: MIT
"""Persistent configuration for calendar accounts, excluding credentials."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit


@dataclass(frozen=True)
class CalendarAccount:
    """Configuration for one independently synchronized calendar account."""

    account_id: str
    provider: str
    username: str
    url: str
    enabled: bool = True

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.account_id):
            raise ValueError("Invalid calendar account ID")
        if self.provider not in {"caldav", "proton"}:
            raise ValueError("Unsupported calendar provider")
        if not self.username.strip() or not isinstance(self.enabled, bool):
            raise ValueError("Invalid calendar account configuration")
        endpoint = urlsplit(self.url)
        if (
            endpoint.scheme not in {"http", "https"}
            or not endpoint.hostname
            or endpoint.username is not None
            or endpoint.password is not None
            or endpoint.query
            or endpoint.fragment
        ):
            raise ValueError("Invalid calendar endpoint")
        if endpoint.scheme == "http" and endpoint.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Remote calendar endpoints require HTTPS")

    @property
    def password_secret(self) -> str:
        """Return the account-specific secret name, not its value."""
        return f"CALENDAR_{self.account_id.upper()}_PASSWORD"


def load_accounts(path: Path) -> tuple[CalendarAccount, ...]:
    """Load configured accounts, rejecting duplicate identifiers."""
    if not path.exists():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Calendar accounts must be a list")
    accounts = tuple(CalendarAccount(**item) for item in data)
    if len({account.account_id for account in accounts}) != len(accounts):
        raise ValueError("Duplicate calendar account ID")
    return accounts


def save_accounts(path: Path, accounts: tuple[CalendarAccount, ...]) -> None:
    """Atomically persist account metadata without storing passwords."""
    if len({account.account_id for account in accounts}) != len(accounts):
        raise ValueError("Duplicate calendar account ID")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            json.dump([asdict(account) for account in accounts], stream, indent=2)
            stream.write("\n")
            stream.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
