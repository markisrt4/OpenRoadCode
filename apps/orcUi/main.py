# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode automotive UI composition root."""

from __future__ import annotations

from apps.orcUi.application_runtime import create_orc_ui_application_runtime
from apps.orcUi.composition.games import configure_games
from apps.orcUi.composition.media import configure_media
from apps.orcUi.composition.radio import configure_radio
from apps.orcUi.orc_ui_app import OrcUiApp

__all__ = ["OrcUiApp", "main"]


def main() -> None:
    runtime = create_orc_ui_application_runtime()
    media_composition = None
    try:
        app = OrcUiApp()
        configure_radio(app, runtime)
        configure_games(app)
        media_composition = configure_media(app, runtime)
        app.schedule_ui_callback(1500, runtime.start_background_apps)
        app.run()
    finally:
        try:
            if media_composition is not None:
                media_composition.close()
        finally:
            runtime.close()


if __name__ == "__main__":
    main()
