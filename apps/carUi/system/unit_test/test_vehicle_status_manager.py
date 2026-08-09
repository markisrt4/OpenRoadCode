"""Tests for vehicle values presented in the Car UI top bar."""

import unittest
from collections.abc import Callable

from apps.carUi.system.vehicle_status_manager import VehicleStatusManager
from ui.system import TopBarUiIf


class RecordingTopBarUi(TopBarUiIf):
    def __init__(self) -> None:
        self.frequencies: list[str] = []
        self.locations: list[str] = []

    def set_title(self, title: str) -> None:
        pass

    def set_back_action(self, action: Callable[[], None]) -> None:
        pass

    def show_back_button(self, text: str | None = None) -> None:
        pass

    def hide_back_button(self) -> None:
        pass

    def invoke_back_action(self) -> None:
        pass

    def set_frequency_text(self, text: str) -> None:
        self.frequencies.append(text)

    def set_location_text(self, text: str) -> None:
        self.locations.append(text)


class VehicleStatusManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.top_bar_ui = RecordingTopBarUi()
        self.manager = VehicleStatusManager(
            top_bar_ui=self.top_bar_ui,
        )

    def test_location_uses_two_decimal_places(self) -> None:
        self.manager.set_location(42.3314, -83.0458)

        self.assertEqual(
            self.top_bar_ui.locations,
            ["🌎 lat.42.33, lon.-83.05"],
        )

    def test_missing_location_uses_placeholder(self) -> None:
        self.manager.set_location(None, None)

        self.assertEqual(self.top_bar_ui.locations, ["🌎 lat.--, lon.--"])

    def test_frequency_is_sent_through_top_bar_contract(self) -> None:
        self.manager.set_frequency(101_900_000)

        self.assertEqual(self.top_bar_ui.frequencies, ["101.900 MHz"])


if __name__ == "__main__":
    unittest.main()
