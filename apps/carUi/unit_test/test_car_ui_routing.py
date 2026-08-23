# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the Car UI menu catalog and route assembly."""

import unittest

from apps.carUi.car_ui_menu_catalog import create_car_ui_menu_pages
from apps.carUi.car_ui_router import CarUiRouter
from apps.carUi.car_ui_routes import register_car_ui_routes


class RecordingScreen:
    def __init__(self, key: str, opened: list[str]) -> None:
        self.key = key
        self.opened = opened

    def show(self) -> None:
        self.opened.append(self.key)


class CarUiRoutingTest(unittest.TestCase):
    def test_menu_destinations_have_registered_routes(self) -> None:
        router, _opened = self._create_router()
        destinations = {
            tile.key
            for page in create_car_ui_menu_pages().values()
            for tile in page.tiles
        }

        self.assertTrue(all(router.contains(key) for key in destinations))

    def test_registered_screen_and_menu_routes_dispatch(self) -> None:
        router, opened = self._create_router()

        router.open("aircraft")
        router.open("media")

        self.assertEqual(opened, ["aircraft", "menu:media"])

    @staticmethod
    def _create_router() -> tuple[CarUiRouter, list[str]]:
        opened: list[str] = []
        router = CarUiRouter()
        register_car_ui_routes(
            router,
            show_menu=lambda key: opened.append(f"menu:{key}"),
            aircraft=RecordingScreen("aircraft", opened),  # type: ignore[arg-type]
            weather=RecordingScreen("weather", opened),  # type: ignore[arg-type]
            lighting=RecordingScreen("lighting", opened),  # type: ignore[arg-type]
            fm_radio=RecordingScreen("fm_radio", opened),  # type: ignore[arg-type]
            scanner_radio=RecordingScreen("scanner_radio", opened),  # type: ignore[arg-type]
            spotify=RecordingScreen("spotify", opened),  # type: ignore[arg-type]
            netflix=RecordingScreen("netflix", opened),  # type: ignore[arg-type]
            youtube=RecordingScreen("youtube", opened),  # type: ignore[arg-type]
            music_visualizer=RecordingScreen(  # type: ignore[arg-type]
                "music_visualizer", opened
            ),
            offroad_dashboard=RecordingScreen(  # type: ignore[arg-type]
                "offroad_dashboard", opened
            ),
            vehicle_gauges=RecordingScreen(  # type: ignore[arg-type]
                "vehicle_gauges", opened
            ),
        )
        return router, opened


if __name__ == "__main__":
    unittest.main()
