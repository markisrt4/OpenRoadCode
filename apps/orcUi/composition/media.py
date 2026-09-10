# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose media screens, services, and presentation resources."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import tkinter as tk

from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from apps.orcUi.managed_browser_media_player import ManagedBrowserMediaPlayer
from apps.orcUi.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from common.xdg_paths import openroadcode_cache_dir
from config.runtime_target import RuntimeTarget, detect_runtime_target
from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.video import MusicVideoController, NetflixPlayer, YouTubeMusicVideo, YouTubePlayer
from frontends.tk.media import BrowserMediaScreen, MediaNavigationBar, MediaScreen, SpotifyNowPlaying, SpotifyScreen
from ui.theme import ThemeMode

MUSIC_VIDEO_PORT = 8770
MUSIC_VIDEO_WINDOW_CLASS = "OpenRoadCodeMusicVideo"
YOUTUBE_WINDOW_CLASS = "openroadcode-youtube"
NETFLIX_WINDOW_CLASS = "openroadcode-netflix"
SPOTIFY_GREEN = "#1DB954"


@dataclass(slots=True)
class MediaComposition:
    music_video_controller: MusicVideoController

    def close(self) -> None:
        self.music_video_controller.stop_video()


def spotify_theme(app: OrcUiApp) -> dict:
    """Use active CSS for chrome and Spotify green for provider actions."""
    theme = copy.deepcopy(SPOTIFY_PANEL_THEME)
    ui = theme_bundle(app.theme_mode).ui
    theme["colors"].update({
        "background": ui.background,
        "card_background": ui.surface,
        "card_border": ui.border,
        "title": ui.text,
        "subtitle": ui.text_muted,
        "detail": ui.text_muted,
        "status": ui.accent_success,
        "button_background": ui.control_background,
        "button_foreground": ui.control_text,
        "button_active_background": SPOTIFY_GREEN,
        "button_active_foreground": "#000000",
        "button_disabled_foreground": ui.text_muted,
        "progress_track": ui.border,
        "progress_fill": SPOTIFY_GREEN,
    })
    return theme


def configure_media(app: OrcUiApp, runtime) -> MediaComposition:
    media = runtime.media
    software_rendering = detect_runtime_target() is RuntimeTarget.LINUX_DEV
    image_cache = ImageCache(max_entries=128, cache_directory=openroadcode_cache_dir("media-art"))
    lyrics = LrclibLyricsClient()
    music_video = YouTubeMusicVideo(
        port=MUSIC_VIDEO_PORT, fullscreen=False, software_rendering=software_rendering,
        window_class=MUSIC_VIDEO_WINDOW_CLASS, show_return_button=False,
    )
    music_video_controller = MusicVideoController(spotify_controller=media.spotify.controller, music_video=music_video)

    def media_navigation(parent: tk.Misc, active: str) -> tk.Widget:
        return MediaNavigationBar(
            parent, theme_bundle=lambda: theme_bundle(app.theme_mode), active=active,
            show_media=lambda: media_screen.show(), show_home=lambda: app.navigate_to("HOME"),
            show_spotify=lambda: spotify_screen.show(), show_youtube=lambda: youtube_screen.show(),
            show_netflix=lambda: netflix_screen.show(),
        )

    spotify_screen = SpotifyScreen(
        app, theme=lambda: spotify_theme(app), back_action=lambda: media_screen.show(),
        image_cache=image_cache, lyrics_client=lyrics, music_video_controller=music_video_controller,
        music_video_presentation=music_video, service=media.spotify,
        local_player=media.spotify_local_player, media_navigation_factory=media_navigation,
    )
    spotify_screen.set_playback_request_handler(media.spotify)
    spotify_screen.set_track_request_handler(media.spotify)
    spotify_screen.set_seek_request_handler(media.spotify)
    spotify_screen.set_volume_request_handler(media.spotify)
    spotify_screen.set_state_loader(media.spotify.latest_state)

    browser_color_scheme = lambda: "dark" if app.theme_mode is ThemeMode.DARK else "light"
    youtube_player = ManagedBrowserMediaPlayer(
        runtime.manager, "youtube", resolve_target=YouTubePlayer.resolve_target,
        preferred_color_scheme=browser_color_scheme,
    )
    netflix_player = ManagedBrowserMediaPlayer(
        runtime.manager, "netflix", resolve_target=NetflixPlayer.validate_url,
        preferred_color_scheme=browser_color_scheme,
    )
    youtube_screen = BrowserMediaScreen(
        "youtube", app, title="YouTube", player=youtube_player,
        default_target="https://www.youtube.com/", window_class=YOUTUBE_WINDOW_CLASS,
        back_action=lambda: media_screen.show(), media_navigation_factory=media_navigation,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )
    netflix_screen = BrowserMediaScreen(
        "netflix", app, title="Netflix", player=netflix_player,
        default_target="https://www.netflix.com/browse", window_class=NETFLIX_WINDOW_CLASS,
        back_action=lambda: media_screen.show(), media_navigation_factory=media_navigation,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )

    def show_spotify_remote() -> None:
        media.spotify_local_player.request_remote()
        media.spotify.request_refresh()
        spotify_screen.show()

    def show_spotify_local() -> None:
        media.spotify_local_player.request_player()
        spotify_screen.show()

    media_screen = MediaScreen(
        app, theme_bundle=lambda: theme_bundle(app.theme_mode),
        show_spotify=spotify_screen.show, show_youtube=youtube_screen.show, show_netflix=netflix_screen.show,
        show_spotify_remote=show_spotify_remote, show_spotify_local=show_spotify_local,
        spotify_local_available=lambda: media.spotify_local_player.state().available,
    )
    app.register_screen("MEDIA", media_screen)
    app.set_home_media_factory(
        lambda parent: SpotifyNowPlaying(
            parent,
            service=media.spotify,
            on_open=spotify_screen.show,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
        )
    )
    return MediaComposition(music_video_controller)
