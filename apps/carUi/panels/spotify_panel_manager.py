from __future__ import annotations

from typing import Optional

from apps.carUi.panels.panel_manager_if import PanelManagerIf
from apps.carUi.panels.spotify_panel import SpotifyPanel
from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.spotify import SpotifyControllerIf
from controllers.video.music_video_controller import MusicVideoController


class SpotifyPanelManager(PanelManagerIf):
    """Create and own the Spotify playback panel."""

    def __init__(
        self,
        app,
        spotify_controller: SpotifyControllerIf,
        music_video_controller: MusicVideoController,
        image_cache: ImageCache | None = None,
        lyrics_client: LrclibLyricsClient | None = None,
    ) -> None:
        super().__init__(app)
        self._spotify_controller = spotify_controller
        self._music_video_controller = music_video_controller
        self._image_cache = image_cache or ImageCache(max_entries=24)
        self._lyrics_client = lyrics_client or LrclibLyricsClient()
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
            music_video_controller=self._music_video_controller,
            image_cache=self._image_cache,
            lyrics_client=self._lyrics_client,
            theme=SPOTIFY_PANEL_THEME,
        )
        panel.pack(fill="both", expand=True)
        panel.start()

        self.spotify_panel = panel
        self.set_status("Spotify controls ready")
