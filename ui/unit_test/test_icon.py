# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for toolkit-independent semantic icon identifiers."""

import unittest

from ui.icon import IconId


class IconIdTest(unittest.TestCase):
    def test_icon_values_are_frontend_neutral_identifiers(self) -> None:
        self.assertEqual("power", IconId.POWER.value)
        self.assertEqual("volume", IconId.VOLUME.value)
        self.assertEqual("volume-muted", IconId.VOLUME_MUTED.value)
        self.assertNotIn("🔊", {icon.value for icon in IconId})


if __name__ == "__main__":
    unittest.main()
