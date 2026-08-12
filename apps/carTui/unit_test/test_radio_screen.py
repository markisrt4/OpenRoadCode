# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the Car TUI radio catalog and interaction."""

import curses
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from apps.carTui.radio_catalog import build_car_tui_radios
from apps.carTui.screens.radio_screen import RadioScreen
from config.runtime_config import RuntimeConfigParser


class FakeWindow:
    def __init__(self, keys: list[int]) -> None:
        self._keys = iter(keys)
        self.timeouts: list[int] = []

    def getch(self) -> int:
        return next(self._keys)

    def timeout(self, milliseconds: int) -> None:
        self.timeouts.append(milliseconds)


class RadioScreenTest(unittest.TestCase):
    @staticmethod
    def _runtime_config():
        project_root = Path(__file__).resolve().parents[3]
        return RuntimeConfigParser(
            project_root / "config" / "runtime.toml",
            project_root=project_root,
        ).load()

    def test_catalog_contains_four_requested_receiver_categories(self) -> None:
        radios = build_car_tui_radios(self._runtime_config(), simulate=True)

        self.assertEqual(
            [radio.key for radio in radios],
            ["fm", "scanner", "airband", "weather"],
        )
        self.assertTrue(all(radio.controller.is_available for radio in radios))

    @patch("apps.carTui.screens.radio_screen.RadioDashboardView.render")
    def test_power_tune_preset_and_switch_band(self, _render: Mock) -> None:
        radios = build_car_tui_radios(self._runtime_config(), simulate=True)
        screen = RadioScreen(radios)
        window = FakeWindow(
            [ord("p"), curses.KEY_RIGHT, ord("]"), ord("3"), ord("p"), ord("b")]
        )

        self.assertTrue(screen.run(window))

        self.assertFalse(any(radio.controller.is_started for radio in radios))
        self.assertEqual(window.timeouts[-1], -1)

    def test_hardware_catalog_uses_shared_configured_radio_stacks(self) -> None:
        radios = build_car_tui_radios(self._runtime_config(), simulate=False)

        self.assertTrue(all(radio.controller.is_available for radio in radios))
        self.assertEqual(radios[0].controller.presets[0].label, "88.7 FM")
        self.assertEqual(radios[2].controller.presets[0].label, "Guard 121.5")
