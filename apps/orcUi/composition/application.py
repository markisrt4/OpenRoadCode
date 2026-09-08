# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level composition for the complete ORC UI application."""

from __future__ import annotations

from dataclasses import dataclass

from apps.orcUi.application_runtime import OrcUiApplicationRuntime, create_orc_ui_application_runtime
from apps.orcUi.composition.games import configure_games
from apps.orcUi.composition.media import MediaComposition, configure_media
from apps.orcUi.composition.radio import configure_radio
from apps.orcUi.orc_ui_app import OrcUiApp


@dataclass(slots=True)
class OrcUiComposition:
    """Own every top-level object created for one ORC UI process."""

    app: OrcUiApp
    runtime: OrcUiApplicationRuntime
    media: MediaComposition

    def run(self) -> None:
        """Start deferred services, run the Tk shell, and close owned resources."""
        self.app.schedule_ui_callback(1500, self.runtime.start_background_apps)
        try:
            self.app.run()
        finally:
            try:
                self.media.close()
            finally:
                self.runtime.close()


def create_orc_ui_composition() -> OrcUiComposition:
    """Create the shell, runtime, and every feature composition in one place."""
    runtime = create_orc_ui_application_runtime()
    try:
        app = OrcUiApp()
        configure_radio(app, runtime)
        configure_games(app)
        media = configure_media(app, runtime)
    except Exception:
        runtime.close()
        raise
    return OrcUiComposition(app=app, runtime=runtime, media=media)
