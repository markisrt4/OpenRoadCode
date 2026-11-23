# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Test CalDAV discovery without contacting a calendar service."""

import unittest
from unittest.mock import patch

from controllers.calendar.caldav_adapter import CalDavAdapter

XML = b"""<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>/caldav/personal/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Personal</d:displayname>
        <d:resourcetype><d:collection/><c:calendar/></d:resourcetype>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/caldav/</d:href>
    <d:propstat>
      <d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""


class FakeSecrets:
    def require_secret(self, name: str) -> str:
        assert name == "CALDAV_BRIDGE_PASSWORD"
        return "example-only"


class FakeResponse:
    status = 207

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size):
        return XML


class CalDavAdapterTests(unittest.TestCase):
    def test_discover_calendar_collections(self) -> None:
        adapter = CalDavAdapter(
            "http://127.0.0.1:8080/caldav/",
            "demo@example.com",
            FakeSecrets(),
            "CALDAV_BRIDGE_PASSWORD",
        )
        with patch("controllers.calendar.caldav_adapter.urlopen", return_value=FakeResponse()) as opener:
            calendars = adapter.discover_calendars()
        self.assertEqual(len(calendars), 1)
        self.assertEqual(calendars[0].display_name, "Personal")
        self.assertEqual(calendars[0].href, "http://127.0.0.1:8080/caldav/personal/")
        request = opener.call_args.args[0]
        self.assertEqual(request.get_method(), "PROPFIND")
        self.assertEqual(request.get_header("Depth"), "1")

    def test_rejects_non_loopback_plaintext(self) -> None:
        with self.assertRaises(ValueError):
            CalDavAdapter("http://example.com/caldav/", "demo", FakeSecrets(), "SECRET")


if __name__ == "__main__":
    unittest.main()
