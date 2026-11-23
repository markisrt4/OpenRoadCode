# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""CalDAV discovery transport shared by Proton, iCloud, and Nextcloud."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from security.secret_manager_if import SecretManagerIf

DAV = "{DAV:}"
CALDAV = "{urn:ietf:params:xml:ns:caldav}"


@dataclass(frozen=True)
class CalDavCalendar:
    href: str
    display_name: str


class CalDavAdapter:
    """Read-only discovery; event sync will be added separately."""

    def __init__(
        self,
        base_url: str,
        username: str,
        secret_manager: SecretManagerIf,
        password_secret_name: str,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("CalDAV URL must use HTTP(S)")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Unencrypted CalDAV is only allowed on loopback")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("CalDAV URL must not contain credentials or fragments")
        self._base_url = base_url.rstrip("/") + "/"
        self._username = username
        self._secrets = secret_manager
        self._password_secret_name = password_secret_name

    def discover_calendars(self) -> list[CalDavCalendar]:
        """Discover direct child calendar collections via DAV PROPFIND."""
        password = self._secrets.require_secret(self._password_secret_name)
        token = base64.b64encode(f"{self._username}:{password}".encode()).decode("ascii")
        request = Request(
            self._base_url,
            data=(
                b'<?xml version="1.0" encoding="utf-8"?>'
                b'<d:propfind xmlns:d="DAV:">'
                b'<d:prop><d:resourcetype/><d:displayname/></d:prop>'
                b'</d:propfind>'
            ),
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
            },
            method="PROPFIND",
        )
        with urlopen(request, timeout=15) as response:
            if response.status != 207:
                raise RuntimeError(f"CalDAV discovery returned HTTP {response.status}")
            document = response.read(2_000_001)
        if len(document) > 2_000_000:
            raise ValueError("CalDAV discovery response too large")
        root = ElementTree.fromstring(document)
        calendars: list[CalDavCalendar] = []
        for item in root.findall(f"{DAV}response"):
            href = item.findtext(f"{DAV}href")
            if not href:
                continue
            for propstat in item.findall(f"{DAV}propstat"):
                status = propstat.findtext(f"{DAV}status", "")
                if " 200 " not in status:
                    continue
                prop = propstat.find(f"{DAV}prop")
                if prop is None:
                    continue
                resource_type = prop.find(f"{DAV}resourcetype")
                if resource_type is None or resource_type.find(f"{CALDAV}calendar") is None:
                    continue
                resolved = urljoin(self._base_url, href)
                if urlsplit(resolved).netloc != urlsplit(self._base_url).netloc:
                    continue
                name = prop.findtext(f"{DAV}displayname") or href.rstrip("/").split("/")[-1]
                calendars.append(CalDavCalendar(resolved, name))
        return calendars
