# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Display profile selection tests; no Tk display required."""
import unittest

from apps.orcUi.frontend.tk.display_profiles import (
    parse_geometry,
    profile_for_geometry,
    select_display_profile,
)


class DisplayProfilesTest(unittest.TestCase):
    def test_original_pi_touch_display(self):
        profile = profile_for_geometry("800x480")
        self.assertEqual(profile.name, "compact")
        self.assertEqual(profile.geometry, "800x480")

    def test_existing_resolutions(self):
        self.assertEqual(profile_for_geometry("1024x600").name, "standard")
        self.assertEqual(profile_for_geometry("1280x720").name, "hd")

    def test_window_position_suffix(self):
        self.assertEqual(parse_geometry("800x480+10-20"), (800, 480))

    def test_reject_invalid_geometry(self):
        for value in ("", "800", "0x480", "800x-480", "abc"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    profile_for_geometry(value)

    def test_reject_nonpositive_dimensions(self):
        with self.assertRaises(ValueError):
            select_display_profile(800, 0)


if __name__ == "__main__":
    unittest.main()
