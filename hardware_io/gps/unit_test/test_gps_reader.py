# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for GPS report decoding compatibility."""

import unittest
from types import SimpleNamespace

from hardware_io.gps.gps_reader import _Python3GpsSession


class Python3GpsSessionTest(unittest.TestCase):
    def test_unpack_decodes_report_without_legacy_encoding_argument(self) -> None:
        session = SimpleNamespace(data=None)

        _Python3GpsSession.unpack(
            session,  # type: ignore[arg-type]
            '{"class":"TPV","lat":43.0}',
        )

        self.assertEqual(session.data.get("class"), "TPV")
        self.assertEqual(session.data.get("lat"), 43.0)

    def test_unpack_wraps_satellite_reports(self) -> None:
        session = SimpleNamespace(data=None)

        _Python3GpsSession.unpack(
            session,  # type: ignore[arg-type]
            '{"class":"SKY","satellites":[{"used":true}]}',
        )

        self.assertTrue(session.data.satellites[0].get("used"))


if __name__ == "__main__":
    unittest.main()
