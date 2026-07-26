from __future__ import annotations

from apps.carUi.panels.panel_manager_if import PanelManagerIf
from apps.carUi.panels.youtube_panel import YouTubePanel
from controllers.video.youtube_player import YouTubePlayer


class YouTubePanelManager(PanelManagerIf):
    """Create and own the YouTube launcher panel."""

    def __init__(self, app, player: YouTubePlayer) -> None:
        super().__init__(app)
        self._player = player

    def show(self) -> None:
        if not self.prepare_panel("YouTube"):
            return
        self.app.top_bar.set_back_command(self.close)
        panel = YouTubePanel(
            self.content_frame,
            player=self._player,
            display=self.app.winfo_screen(),
            set_status=self.set_status,
            on_return=self.close,
            colors=self.app.colors,
        )
        panel.pack(fill="both", expand=True)
        self.set_status("YouTube ready")

    def close(self) -> None:
        self._player.stop()
        self.app.show_menu("media")

