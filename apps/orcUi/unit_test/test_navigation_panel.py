# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for ORC navigation panel camera and POI controls."""

import unittest
from unittest.mock import Mock

from apps.orcUi.navigation_panel import NavigationPanel
from controllers.poi import PoiCategory


class NavigationPanelControlTest(unittest.TestCase):
    """Verify semantic requests without requiring an X display."""

    def _panel(self) -> NavigationPanel:
        panel = object.__new__(NavigationPanel)
        panel._request_handler = Mock()
        panel._zoom_level = 16.5
        panel._follow_enabled = True
        panel.set_follow_enabled = Mock(
            side_effect=lambda enabled: setattr(panel, "_follow_enabled", enabled)
        )
        return panel

    def test_manual_zoom_disables_follow_and_requests_zoom(self) -> None:
        panel = self._panel()

        panel._change_zoom(1.0)

        panel.set_follow_enabled.assert_called_once_with(False)
        panel._request_handler.request_zoom.assert_called_once_with(17.5)

    def test_north_up_disables_follow(self) -> None:
        panel = self._panel()

        panel._north_up()

        panel.set_follow_enabled.assert_called_once_with(False)
        panel._request_handler.request_bearing.assert_called_once_with(0.0)

    def test_recenter_restores_follow(self) -> None:
        panel = self._panel()
        panel._follow_enabled = False

        panel._recenter()

        panel.set_follow_enabled.assert_called_once_with(True)
        panel._request_handler.request_recenter.assert_called_once_with()

    def test_toggle_follow_emits_semantic_request(self) -> None:
        panel = self._panel()

        panel._toggle_follow()

        panel.set_follow_enabled.assert_called_once_with(False)
        panel._request_handler.request_follow.assert_called_once_with(False)

    def test_gas_shortcut_starts_fuel_search(self) -> None:
        panel = self._panel()
        panel._start_poi_search = Mock()

        panel._destination_shortcut("gas")

        panel._start_poi_search.assert_called_once_with(PoiCategory.FUEL)

    def test_grocery_shortcut_starts_grocery_search(self) -> None:
        panel = self._panel()
        panel._start_poi_search = Mock()

        panel._destination_shortcut("grocery")

        panel._start_poi_search.assert_called_once_with(PoiCategory.GROCERY)

    def test_food_shortcut_starts_food_search(self) -> None:
        panel = self._panel()
        panel._start_poi_search = Mock()

        panel._destination_shortcut("food")

        panel._start_poi_search.assert_called_once_with(PoiCategory.FOOD)

    def test_issue_poi_search_forwards_to_controller(self) -> None:
        panel = self._panel()
        panel._poi_controller = Mock()
        panel._shortcut_status = Mock()
        panel._poi_search_after_id = "pending"

        panel._issue_poi_search(PoiCategory.FUEL)

        self.assertIsNone(panel._poi_search_after_id)
        panel._poi_controller.search.assert_called_once_with(PoiCategory.FUEL)
        panel._shortcut_status.set.assert_called_once_with("Searching nearby fuel…")


if __name__ == "__main__":
    unittest.main()
