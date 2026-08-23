# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib.util
import unittest

EVDEV_AVAILABLE = importlib.util.find_spec("evdev") is not None
if EVDEV_AVAILABLE:
    from hardware_io.keyboard import KeyboardReader
else:
    KeyboardReader = None  # type: ignore[assignment,misc]


@unittest.skipUnless(EVDEV_AVAILABLE, "optional evdev dependency is not installed")
class KeyboardReaderTest(unittest.TestCase):
    def test_normalize_keycode_preserves_a_key_name(self) -> None:
        self.assertEqual(
            KeyboardReader._normalize_keycode("KEY_ENTER"),
            "KEY_ENTER",
        )

    def test_normalize_keycode_selects_the_first_alias(self) -> None:
        self.assertEqual(
            KeyboardReader._normalize_keycode(["KEY_HANGUEL", "KEY_HANGEUL"]),
            "KEY_HANGUEL",
        )

    def test_normalize_keycode_rejects_an_empty_alias_list(self) -> None:
        with self.assertRaisesRegex(ValueError, "did not contain a keycode"):
            KeyboardReader._normalize_keycode([])


if __name__ == "__main__":
    unittest.main()
