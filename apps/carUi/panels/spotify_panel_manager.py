from __future__ import annotations

from typing import Optional

from apps.carUi.panels.panel_manager_if import PanelManagerIf
from apps.carUi.panels.spotify_panel import SpotifyPanel
from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from controllers.spotify import SpotifyControllerIf


class SpotifyPanelManager(PanelManagerIf):
    """Create and own the Spotify playback panel."""

    def __init__(
        self,
        app,
        spotify_controller: SpotifyControllerIf,
    ) -> None:
        super().__init__(app)
        self._spotify_controller = spotify_controller
        self.spotify_panel: Optional[SpotifyPanel] = None

    def show(self) -> None:
        if not self.prepare_panel("Spotify"):
            return

        self.app.top_bar.set_title("Spotify")
        self.app.top_bar.set_back_command(
            lambda: self.app.show_menu("media")
        )
        self.app.top_bar.show_back_button()

        panel = SpotifyPanel(
            parent=self.content_frame,
            controller=self._spotify_controller,
            theme=SPOTIFY_PANEL_THEME,
        )
        panel.pack(fill="both", expand=True)
        panel.start()

        self.spotify_panel = panel
        self.set_status("Spotify controls ready")
