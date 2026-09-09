# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level composition for the complete ORC UI application."""

from __future__ import annotations

from dataclasses import dataclass

from apps.orcUi.application_runtime import OrcUiApplicationRuntime, create_orc_ui_application_runtime
from apps.orcUi.composition.core import CoreComposition, create_core_composition
from apps.orcUi.composition.games import configure_games
from apps.orcUi.composition.media import MediaComposition, configure_media
from apps.orcUi.composition.radio import configure_radio
from apps.orcUi.orc_ui_app import OrcUiApp


@dataclass(slots=True)
class OrcUiComposition:
    """Own every top-level object created for one ORC UI process."""

    core: CoreComposition
    runtime: OrcUiApplicationRuntime
    media: MediaComposition

    @property
    def app(self) -> OrcUiApp:
        return self.core.app

    def run(self) -> None:
        """Start ingress/services, run Tk, and close resources in reverse order."""
        try:
            self.app.schedule_ui_callback(1500, self.runtime.start_background_apps)
            self.core.start()
            self.app.run()
        finally:
            try:
                self.media.close()
            finally:
                try:
                    self.core.close()
                finally:
                    self.runtime.close()


def create_orc_ui_composition() -> OrcUiComposition:
    """Create all shell, runtime, and feature dependencies in one place."""
    runtime = create_orc_ui_application_runtime()
    core: CoreComposition | None = None
    try:
        core = create_core_composition()
        app = core.app
        configure_radio(app, runtime)
        configure_games(app)
        media = configure_media(app, runtime)
    except Exception:
        if core is not None:
            core.close()
        runtime.close()
        raise
    return OrcUiComposition(core=core, runtime=runtime, media=media)
