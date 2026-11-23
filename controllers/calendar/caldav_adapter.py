# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only CalDAV collection discovery across compliant providers."""

from __future__ import annotations

import base64
from urllib.error import HTTPError
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

from security.secret_manager_if import SecretManagerIf

DAV = "{DAV:}"
CALDAV = "{urn:ietf:params:xml:ns:caldav}"
_MAX_RESPONSE = 2_000_000


@dataclass(frozen=True)
class CalDavCalendar:
    href: str
    display_name: str


class CalDavAuthenticationError(RuntimeError):
    """The CalDAV server rejected the configured account credentials."""


class CalDavHttpError(RuntimeError):
    """The CalDAV server returned an unexpected HTTP status."""


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        """Never forward credentials to a redirected destination."""
        return None


class CalDavAdapter:
    """Discover calendars without provider-specific Proton dependencies."""

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
        if parsed.username or parsed.password or parsed.fragment or parsed.query:
            raise ValueError("CalDAV URL must not contain credentials, queries or fragments")
        self._base_url = base_url.rstrip("/") + "/"
        self._username = username
        self._secrets = secret_manager
        self._password_secret_name = password_secret_name

    def _resolve(self, base: str, href: str) -> str:
        resolved = urljoin(base, href)
        original = urlsplit(self._base_url)
        target = urlsplit(resolved)
        if (target.scheme, target.netloc) != (original.scheme, original.netloc):
            raise ValueError("CalDAV reference leaves the configured server")
        if target.username or target.password or target.fragment:
            raise ValueError("Invalid CalDAV reference")
        return resolved

    def _propfind(self, url: str, depth: int, properties: bytes) -> ElementTree.Element:
        password = self._secrets.require_secret(self._password_secret_name)
        token = base64.b64encode(f"{self._username}:{password}".encode()).decode("ascii")
        payload = (
            b'<?xml version="1.0" encoding="utf-8"?>'
            b'<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
            b"<d:prop>" + properties + b"</d:prop></d:propfind>"
        )
        request = Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": str(depth),
            },
            method="PROPFIND",
        )
        try:
            with build_opener(_NoRedirects()).open(request, timeout=15) as response:
                if response.status != 207:
                    raise CalDavHttpError(
                        f"CalDAV discovery returned HTTP {response.status}"
                    )
                document = response.read(_MAX_RESPONSE + 1)
        except HTTPError as error:
            if error.code == 401:
                raise CalDavAuthenticationError(
                    "CalDAV authentication failed (HTTP 401). "
                    "Check the full account username and bridge password."
                ) from None
            raise CalDavHttpError(
                f"CalDAV discovery returned HTTP {error.code}"
            ) from None
        if len(document) > _MAX_RESPONSE:
            raise ValueError("CalDAV discovery response too large")
        return ElementTree.fromstring(document)

    @staticmethod
    def _properties(root: ElementTree.Element):
        for response in root.findall(f"{DAV}response"):
            href = response.findtext(f"{DAV}href")
            for propstat in response.findall(f"{DAV}propstat"):
                status = propstat.findtext(f"{DAV}status", "")
                if " 200 " not in status:
                    continue
                prop = propstat.find(f"{DAV}prop")
                if prop is not None:
                    yield href, prop

    def discover_calendars(self) -> list[CalDavCalendar]:
        """Follow current-user-principal and calendar-home-set, then list collections."""
        principal_doc = self._propfind(
            self._base_url, 0, b"<d:current-user-principal/>"
        )
        principal = next(
            (
                href
                for _, prop in self._properties(principal_doc)
                if (href := prop.findtext(f"{DAV}current-user-principal/{DAV}href"))
            ),
            None,
        )
        home_url = self._base_url
        if principal:
            principal_url = self._resolve(self._base_url, principal)
            home_doc = self._propfind(
                principal_url, 0, b"<c:calendar-home-set/>"
            )
            home_href = next(
                (
                    href
                    for _, prop in self._properties(home_doc)
                    if (href := prop.findtext(f"{CALDAV}calendar-home-set/{DAV}href"))
                ),
                None,
            )
            if home_href:
                home_url = self._resolve(principal_url, home_href)
        collection_doc = self._propfind(
            home_url, 1, b"<d:resourcetype/><d:displayname/>"
        )
        calendars: list[CalDavCalendar] = []
        seen: set[str] = set()
        for href, prop in self._properties(collection_doc):
            if not href:
                continue
            resource_type = prop.find(f"{DAV}resourcetype")
            if resource_type is None or resource_type.find(f"{CALDAV}calendar") is None:
                continue
            resolved = self._resolve(home_url, href)
            if resolved in seen:
                continue
            seen.add(resolved)
            name = prop.findtext(f"{DAV}displayname") or href.rstrip("/").split("/")[-1]
            calendars.append(CalDavCalendar(resolved, name))
        return calendars
