# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Aircraft menu presentation behavior without requiring a Tk display."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from apps.orcUi.frontend.tk.bottom_bar import (
    OrcUiBottomBar,
    aircraft_button_text,
    aircraft_menu_labels,
)
from ui.radio import AircraftMenuUiState


class BottomBarAircraftTest(unittest.TestCase):
    def test_enabled_status_shows_aircraft_count(self) -> None:
        self.assertEqual("✈  AIRCRAFT ▾", aircraft_button_text(enabled=True, aircraft_count=7))

    def test_disabled_status_and_menu_are_explicit(self) -> None:
        self.assertEqual("✈  AIRCRAFT ▾", aircraft_button_text(enabled=False, aircraft_count=9))
        receiver, tracker, airband = aircraft_menu_labels(enabled=False, aircraft_count=9)
        self.assertIn("receiver off", receiver)
        self.assertEqual("↗  Open 1090 aircraft map", tracker)
        self.assertEqual("♫  Open AM / pilot radio", airband)

    def test_toggle_emits_nonblocking_semantic_request(self) -> None:
        handler = Mock()
        panel = SimpleNamespace(
            _aircraft_handler=handler,
            _adsb_enabled=False,
            _aircraft_count=3,
        )

        OrcUiBottomBar._toggle_adsb(panel)

        handler.request_adsb_enabled.assert_called_once_with(True)

    def test_aircraft_state_normalizes_count(self) -> None:
        self.assertEqual(0, AircraftMenuUiState(True, -2).aircraft_count)

    def test_nonzero_active_count_is_available_inside_menu(self) -> None:
        _receiver, tracker, _airband = aircraft_menu_labels(enabled=True, aircraft_count=7)
        self.assertEqual("↗  Open 1090 aircraft map · 7 nearby", tracker)

    def test_expanded_aircraft_button_collapses_existing_popup(self) -> None:
        panel = SimpleNamespace(_aircraft_popup=Mock(), _close_aircraft_menu=Mock())

        OrcUiBottomBar._show_aircraft_menu(panel)

        panel._close_aircraft_menu.assert_called_once_with()

    def test_aircraft_action_closes_popup_before_dispatch(self) -> None:
        events = []
        panel = SimpleNamespace(_close_aircraft_menu=lambda: events.append("close"))

        OrcUiBottomBar._run_aircraft_action(panel, lambda: events.append("action"))

        self.assertEqual(["close", "action"], events)


if __name__ == "__main__":
    unittest.main()
