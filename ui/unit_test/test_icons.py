# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for toolkit-independent icon contracts."""

import unittest

from ui import IconId
from ui.menu.menu_icons import menu_icon_for_key


class IconContractTest(unittest.TestCase):
    def test_menu_keys_resolve_to_semantic_icons(self) -> None:
        self.assertIs(menu_icon_for_key("radio"), IconId.RADIO)
        self.assertIs(menu_icon_for_key("spotify"), IconId.SPOTIFY)
        self.assertIs(menu_icon_for_key("weather_dashboard"), IconId.WEATHER)

    def test_unknown_menu_key_has_no_forced_icon(self) -> None:
        self.assertIsNone(menu_icon_for_key("future-feature"))

    def test_icon_values_are_frontend_neutral_names(self) -> None:
        self.assertEqual("camera", IconId.CAMERA.value)
        self.assertEqual("volume-muted", IconId.VOLUME_MUTED.value)


if __name__ == "__main__":
    unittest.main()
