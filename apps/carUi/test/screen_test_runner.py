"""Launch one screen inside the real Car UI shell for visual testing."""

from __future__ import annotations

import argparse
import os

from apps.carUi.car_ui_frontend import CarUiFrontend
from apps.carUi.car_ui_startup import (
    build_car_ui_dependencies,
    log_startup_status,
)
from frontends.tk.runtime import configure_display
from ui.screen_ui_if import ScreenId


ROUTE_ALIASES = {"scanner": "scanner_radio"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch one Car UI screen for visual testing."
    )
    parser.add_argument(
        "screen",
        choices=(
            "spotify",
            "netflix",
            "youtube",
            "lighting",
            "weather",
            "fm_radio",
            "scanner",
            "aircraft",
            "offroad_dashboard",
        ),
    )
    parser.add_argument("--geometry", default="800x480")
    parser.add_argument("--fullscreen", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["CARUI_GEOMETRY"] = args.geometry
    os.environ["CARUI_FULLSCREEN"] = "1" if args.fullscreen else "0"
    os.environ["CARUI_SPLASH"] = "0"
    configure_display()

    dependencies = build_car_ui_dependencies(log_startup_status)
    app: CarUiFrontend | None = None
    try:
        app = CarUiFrontend(dependencies, title=f"Screen Test: {args.screen}")
        route = ROUTE_ALIASES.get(args.screen, args.screen)
        app.show_screen(ScreenId(route))
        app.run()
    finally:
        try:
            if app is not None:
                app.shutdown()
        finally:
            dependencies.close()


if __name__ == "__main__":
    main()
