from __future__ import annotations

from apps.carUi.panels.netflix_panel import NetflixPanel
from apps.carUi.panels.panel_manager_if import PanelManagerIf
from controllers.video.netflix_player import NetflixPlayer


class NetflixPanelManager(PanelManagerIf):
    """Create and own the Netflix launcher panel."""

    def __init__(self, app, player: NetflixPlayer) -> None:
        super().__init__(app)
        self._player = player

    def show(self) -> None:
        if not self.prepare_panel("Netflix"):
            return
        self.app.top_bar.set_back_command(self.close)
        panel = NetflixPanel(
            self.content_frame,
            player=self._player,
            display=self.app.winfo_screen(),
            set_status=self.set_status,
            on_return=self.close,
            colors=self.app.colors,
        )
        panel.pack(fill="both", expand=True)
        self.set_status("Netflix ready")

    def close(self) -> None:
        self._player.stop()
        self.app.show_menu("media")
