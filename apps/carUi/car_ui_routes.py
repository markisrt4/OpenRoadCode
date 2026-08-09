"""Route registration for the screens assembled by Car UI."""

from collections.abc import Callable

from apps.carUi.car_ui_router import CarUiRouter
from ui.screen_ui_if import ScreenUiIf


def register_car_ui_routes(
    router: CarUiRouter,
    *,
    show_menu: Callable[[str], None],
    aircraft: ScreenUiIf,
    weather: ScreenUiIf,
    lighting: ScreenUiIf,
    fm_radio: ScreenUiIf,
    scanner_radio: ScreenUiIf,
    spotify: ScreenUiIf,
    offroad_dashboard: ScreenUiIf,
) -> None:
    """Register the destinations available in the standard Car UI."""
    router.register_many(
        {
            "radio": lambda: show_menu("radio"),
            "aircraft": aircraft.show,
            "gauges": lambda: show_menu("gauges"),
            "weather": weather.show,
            "lighting": lighting.show,
            "media": lambda: show_menu("media"),
            "fm_radio": fm_radio.show,
            "scanner_radio": scanner_radio.show,
            "spotify": spotify.show,
            "offroad_dashboard": offroad_dashboard.show,
        }
    )
