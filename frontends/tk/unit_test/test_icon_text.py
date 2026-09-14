# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Tk rendering of semantic UI icons."""

import unittest

from frontends.tk.icon_text import icon_text
from ui.icon import IconId


class IconTextTest(unittest.TestCase):
    def test_shell_icons_have_tk_text_renderings(self) -> None:
        for icon in (
            IconId.POWER,
            IconId.MICROPHONE,
            IconId.CAMERA,
            IconId.DISPLAY,
            IconId.BRIGHTNESS,
            IconId.VOLUME,
            IconId.VOLUME_MUTED,
        ):
            self.assertTrue(icon_text(icon), icon)

    def test_non_text_icon_may_be_rendered_by_another_tk_component(self) -> None:
        self.assertEqual("", icon_text(IconId.RADIO))


if __name__ == "__main__":
    unittest.main()
