# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest
from pathlib import Path

from config.runtime_config import (
    RuntimeConfigError,
    RuntimeConfigParser,
)


class InputDeviceConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = RuntimeConfigParser(
            Path("unused.toml"), require_radio_files=False
        )

    def test_parses_optional_keyboard_and_pushbuttons(self) -> None:
        config = self.parser._parse_input({
            "keyboard": {"enabled": True, "device_path": "/dev/input/event3"},
            "push_buttons": [
                {"pin": 11, "action": "home"},
                {"pin": 13, "action": "back", "active_low": False},
            ],
        })

        self.assertTrue(config.keyboard.enabled)
        self.assertEqual(config.keyboard.device_path, "/dev/input/event3")
        self.assertEqual([item.action for item in config.push_buttons], ["home", "back"])

    def test_rejects_unknown_pushbutton_action(self) -> None:
        with self.assertRaises(RuntimeConfigError):
            self.parser._parse_input({
                "push_buttons": [{"pin": 11, "action": "self_destruct"}]
            })


if __name__ == "__main__":
    unittest.main()
