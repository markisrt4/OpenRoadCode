# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Mock CalDAV discovery chain and security tests."""

import unittest
from datetime import datetime, timezone
from urllib.error import HTTPError
from unittest.mock import patch

from controllers.calendar.caldav_adapter import (
    CalDavAdapter,
    CalDavCalendar,
    CalDavAuthenticationError,
    CalDavHttpError,
)


def multistatus(href: str, properties: str) -> bytes:
    return (
        '<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
        f"<d:response><d:href>{href}</d:href><d:propstat><d:prop>{properties}</d:prop>"
        "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"
        "</d:multistatus>"
    ).encode()


PRINCIPAL = multistatus(
    "/caldav/principal/",
    "<d:current-user-principal><d:href>/caldav/principal/</d:href></d:current-user-principal>",
)
HOME = multistatus(
    "/caldav/principal/",
    "<c:calendar-home-set><d:href>/caldav/principal/calendars/</d:href></c:calendar-home-set>",
)
CALENDAR = multistatus(
    "/caldav/principal/calendars/personal/",
    "<d:displayname>Personal</d:displayname>"
    "<d:resourcetype><d:collection/><c:calendar/></d:resourcetype>",
)


class FakeSecrets:
    def require_secret(self, name: str) -> str:
        assert name == "CALDAV_BRIDGE_PASSWORD"
        return "example-only"


class FakeResponse:
    status = 207

    def __init__(self, data: bytes) -> None:
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size):
        return self.data


class FakeOpener:
    def __init__(self, responses: list[bytes]) -> None:
        self.responses = iter(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        return FakeResponse(next(self.responses))


class CalDavAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = CalDavAdapter(
            "http://127.0.0.1:8080/caldav/",
            "demo@example.com",
            FakeSecrets(),
            "CALDAV_BRIDGE_PASSWORD",
        )

    def test_follows_principal_and_home(self) -> None:
        opener = FakeOpener([PRINCIPAL, HOME, CALENDAR])
        with patch("controllers.calendar.caldav_adapter.build_opener", return_value=opener):
            calendars = self.adapter.discover_calendars()
        self.assertEqual(
            [(item.display_name, item.href) for item in calendars],
            [("Personal", "http://127.0.0.1:8080/caldav/principal/calendars/personal/")],
        )
        self.assertEqual(
            [request.full_url for request in opener.requests],
            [
                "http://127.0.0.1:8080/caldav/",
                "http://127.0.0.1:8080/caldav/principal/",
                "http://127.0.0.1:8080/caldav/principal/calendars/",
            ],
        )
        self.assertEqual(
            [request.get_header("Depth") for request in opener.requests], ["0", "0", "1"]
        )

    def test_falls_back_to_base_when_no_principal(self) -> None:
        empty = multistatus("/caldav/", "<d:displayname>Root</d:displayname>")
        opener = FakeOpener([empty, CALENDAR])
        with patch("controllers.calendar.caldav_adapter.build_opener", return_value=opener):
            calendars = self.adapter.discover_calendars()
        self.assertEqual(len(calendars), 1)

    def test_rejects_cross_origin_calendar_home(self) -> None:
        external = multistatus(
            "/caldav/principal/",
            "<c:calendar-home-set><d:href>https://evil.example/cal/</d:href></c:calendar-home-set>",
        )
        opener = FakeOpener([PRINCIPAL, external])
        with patch("controllers.calendar.caldav_adapter.build_opener", return_value=opener):
            with self.assertRaises(ValueError):
                self.adapter.discover_calendars()

    def test_unauthorized_is_authentication_error(self) -> None:
        opener = FakeOpener([])
        with patch("controllers.calendar.caldav_adapter.build_opener", return_value=opener):
            with patch.object(
                opener,
                "open",
                side_effect=HTTPError(
                    "http://127.0.0.1:8080/caldav/", 401, "Unauthorized", {}, None
                ),
            ):
                with self.assertRaisesRegex(CalDavAuthenticationError, "full account username"):
                    self.adapter.discover_calendars()

    def test_forbidden_is_not_authentication_error(self) -> None:
        opener = FakeOpener([])
        with patch("controllers.calendar.caldav_adapter.build_opener", return_value=opener):
            with patch.object(
                opener,
                "open",
                side_effect=HTTPError("http://127.0.0.1:8080/caldav/", 403, "Forbidden", {}, None),
            ):
                with self.assertRaisesRegex(CalDavHttpError, "403"):
                    self.adapter.discover_calendars()

    def test_calendar_query_returns_icalendar_and_etag(self) -> None:
        report = multistatus(
            "/caldav/principal/calendars/personal/meeting.ics",
            "<d:getetag>&quot;revision-1&quot;</d:getetag>"
            "<c:calendar-data>BEGIN:VCALENDAR\\nBEGIN:VEVENT\\nUID:abc\\nEND:VEVENT\\nEND:VCALENDAR</c:calendar-data>",
        )
        opener = FakeOpener([report])
        with patch("controllers.calendar.caldav_adapter.build_opener", return_value=opener):
            resources = self.adapter.query_event_resources(
                CalDavCalendar(
                    "http://127.0.0.1:8080/caldav/principal/calendars/personal/",
                    "Personal",
                ),
                datetime(2026, 11, 1, tzinfo=timezone.utc),
                datetime(2026, 12, 1, tzinfo=timezone.utc),
            )
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].etag, '"revision-1"')
        self.assertIn("BEGIN:VEVENT", resources[0].icalendar)
        request = opener.requests[0]
        self.assertEqual(request.get_method(), "REPORT")
        self.assertEqual(request.get_header("Depth"), "1")
        self.assertIn(b"20261101T000000Z", request.data)
        self.assertIn(b"20261201T000000Z", request.data)

    def test_calendar_query_rejects_invalid_range(self) -> None:
        calendar = CalDavCalendar("http://127.0.0.1:8080/caldav/personal/", "Personal")
        with self.assertRaises(ValueError):
            self.adapter.query_event_resources(
                calendar,
                datetime(2026, 11, 1),
                datetime(2026, 12, 1, tzinfo=timezone.utc),
            )

    def test_calendar_query_rejects_cross_origin(self) -> None:
        calendar = CalDavCalendar("https://other.example/calendar/", "Other")
        with self.assertRaises(ValueError):
            self.adapter.query_event_resources(
                calendar,
                datetime(2026, 11, 1, tzinfo=timezone.utc),
                datetime(2026, 12, 1, tzinfo=timezone.utc),
            )

    def test_rejects_non_loopback_plaintext(self) -> None:
        with self.assertRaises(ValueError):
            CalDavAdapter("http://example.com/caldav/", "demo", FakeSecrets(), "SECRET")


if __name__ == "__main__":
    unittest.main()
