# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Calendar selection persistence tests."""

import tempfile
import unittest
from pathlib import Path

from controllers.calendar.calendar_selection import (
    load_disabled_calendar_ids,
    save_disabled_calendar_ids,
)


class CalendarSelectionTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "selection.json"
            self.assertEqual(load_disabled_calendar_ids(path), frozenset())
            save_disabled_calendar_ids(path, {"caldav://b", "caldav://a"})
            self.assertEqual(load_disabled_calendar_ids(path), {"caldav://a", "caldav://b"})

    def test_rejects_invalid_format(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "selection.json"
            path.write_text('{"disabled_calendar_ids": [42]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_disabled_calendar_ids(path)
