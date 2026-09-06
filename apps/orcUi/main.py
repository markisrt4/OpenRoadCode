# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode automotive UI composition root."""

from __future__ import annotations

import copy
from pathlib import Path
import tkinter as tk

from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.application_runtime import create_orc_ui_application_runtime
from apps.orcUi.orc_ui_app import OrcUiApp
from apps.orcUi.radio_application_service import RadioApplicationServiceIf
from apps.orcUi.radio_entry_panel import RadioEntryPanel
from apps.orcUi.theme_runtime import theme_bundle
from config.runtime_target import RuntimeTarget, detect_runtime_target
from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.video import MusicVideoController, NetflixPlayer, YouTubeMusicVideo, YouTubePlayer
from frontends.tk.games import GamesScreen
from frontends.tk.media import BrowserMediaScreen, MediaScreen, NetflixPanel, SpotifyScreen, YouTubePanel
from frontends.tk.radio import RadioScreen
from frontends.x11 import X11WindowEmbedder
from ui.theme import ThemeBundle, ThemeMode

__all__ = ["OrcUiApp", "main"]

SPOTIFY_GREEN = "#1DB954"
MUSIC_VIDEO_PORT = 8770
MUSIC_VIDEO_WINDOW_CLASS = "OpenRoadCodeMusicVideo"


def _create_radio_panel(
    parent: tk.Misc,
    embedder: X11WindowEmbedder,
    theme: ThemeBundle,
    radio_application: RadioApplicationServiceIf,
) -> RadioEntryPanel:
    return RadioEntryPanel(
        parent,
        embedder=embedder,
        theme=theme,
        radio_application=radio_application,
    )


def _sync_radio_theme(mode: ThemeMode) -> None:
    sync_sdrpp_theme("Light" if mode is ThemeMode.LIGHT else "Dark")


def _spotify_theme(app: OrcUiApp) -> dict:
    """Adapt the reusable Spotify presentation theme to the ORC shell."""
    ui = theme_bundle(app.theme_mode).ui
    theme = copy.deepcopy(SPOTIFY_PANEL_THEME)
    theme["colors"].update(
        {
            "background": ui.background,
            "card_background": ui.surface,
            "card_border": ui.border,
            "title": ui.text,
            "subtitle": ui.text_muted,
            "detail": ui.text_muted,
            "status": SPOTIFY_GREEN,
            "button_background": ui.control_background,
            "button_foreground": ui.control_text,
            "button_active_background": SPOTIFY_GREEN,
            "button_active_foreground": "#000000",
            "button_disabled_foreground": ui.text_muted,
            "progress_track": ui.border,
            "progress_fill": SPOTIFY_GREEN,
        }
    )
    return theme


def _browser_colors(app: OrcUiApp, *, accent: str) -> dict[str, str]:
    ui = theme_bundle(app.theme_mode).ui
    return {
        "app_bg": ui.background,
        "tile_bg": ui.surface,
        "tile_border": ui.border,
        "tile_title": ui.text,
        "tile_subtitle": ui.text_muted,
        "tile_detail": ui.text_muted,
        "tile_accent": accent,
    }


def main() -> None:
    """Compose and run the integrated OpenRoadCode UI."""
    application_runtime = create_orc_ui_application_runtime()
    media = application_runtime.media
    app = OrcUiApp()

    app.register_screen(
        "RADIO",
        RadioScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_mode=lambda: app.theme_mode,
            panel_factory=lambda parent, embedder, theme: _create_radio_panel(
                parent,
                embedder,
                theme,
                application_runtime.radio,
            ),
            sync_theme=_sync_radio_theme,
        ),
    )
    app.register_screen(
        "GAMES",
        GamesScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            theme_mode=lambda: app.theme_mode,
        ),
    )

    runtime_target = detect_runtime_target()
    software_rendering = runtime_target is RuntimeTarget.LINUX_DEV
    image_cache = ImageCache(
        max_entries=128,
        cache_directory=Path.home() / ".cache" / "openroadcode" / "media-art",
    )
    lyrics = LrclibLyricsClient()
    music_video = YouTubeMusicVideo(
        port=MUSIC_VIDEO_PORT,
        fullscreen=False,
        software_rendering=software_rendering,
        window_class=MUSIC_VIDEO_WINDOW_CLASS,
        show_return_button=False,
    )
    music_video_controller = MusicVideoController(
        spotify_controller=media.spotify.controller,
        music_video=music_video,
    )
    spotify_screen = SpotifyScreen(
        app,
        theme=_spotify_theme(app),
        back_action=lambda: media_screen.show(),
        image_cache=image_cache,
        lyrics_client=lyrics,
        music_video_controller=music_video_controller,
    )
    spotify_screen.set_playback_request_handler(media.spotify)
    spotify_screen.set_track_request_handler(media.spotify)
    spotify_screen.set_seek_request_handler(media.spotify)
    spotify_screen.set_volume_request_handler(media.spotify)
    spotify_screen.set_state_loader(media.spotify.latest_state)

    youtube_player = YouTubePlayer(
        software_rendering=software_rendering,
        dark_mode=app.theme_mode is ThemeMode.DARK,
    )
    netflix_player = NetflixPlayer(
        software_rendering=software_rendering,
        dark_mode=app.theme_mode is ThemeMode.DARK,
    )
    youtube_screen = BrowserMediaScreen(
        "youtube",
        app,
        title="YouTube",
        player=youtube_player,
        panel_factory=lambda parent, player, display, status, back: YouTubePanel(
            parent,
            player=player,
            default_url="https://www.youtube.com/",
            display=display,
            set_status=status,
            on_return=back,
            colors=_browser_colors(app, accent="#FF0033"),
        ),
        back_action=lambda: media_screen.show(),
    )
    netflix_screen = BrowserMediaScreen(
        "netflix",
        app,
        title="Netflix",
        player=netflix_player,
        panel_factory=lambda parent, player, display, status, back: NetflixPanel(
            parent,
            player=player,
            default_url="https://www.netflix.com/browse",
            display=display,
            set_status=status,
            on_return=back,
            colors=_browser_colors(app, accent="#E50914"),
        ),
        back_action=lambda: media_screen.show(),
    )
    media_screen = MediaScreen(
        app,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
        show_spotify=spotify_screen.show,
        show_youtube=youtube_screen.show,
        show_netflix=netflix_screen.show,
    )
    app.register_screen("MEDIA", media_screen)

    # Keep heavyweight optional applications out of the critical UI startup
    # path. Once Tk has presented the shell, the shared lifecycle controller
    # applies PRELOAD/PERSISTENT policy and starts media state warming on its
    # background workers.
    app.schedule_ui_callback(1500, application_runtime.start_background_apps)
    try:
        app.run()
    finally:
        music_video_controller.stop_video()
        youtube_player.stop()
        netflix_player.stop()
        application_runtime.close()


if __name__ == "__main__":
    main()
