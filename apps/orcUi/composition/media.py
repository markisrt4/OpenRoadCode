# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Compose media screens, services, and presentation resources."""

from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import os
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, field

from common.resource_cleanup import ResourceCleanup, close_resources

from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from apps.common.spotify_presentation_factory import create_spotify_presentation, cached_artwork_loader
from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from frontends.tk.media.music_visualizer_screen import MusicVisualizerScreen
from apps.orcUi.composition.music_visualizer import create_browser_visualizer, create_music_visualizer_session, selected_music_visualizer_source
from apps.orcUi.adapters.music_visualizer_browser import MusicVisualizerBrowser, WINDOW_CLASS
from controllers.audio.music_analysis.music_visualizer_controller import MusicVisualizerController
from apps.orcUi.theme_runtime import theme_bundle
from common.xdg_paths import openroadcode_cache_dir
from config.runtime_target import RuntimeTarget, detect_runtime_target
from controllers.spotify.spotify_presentation import SpotifyPresentation
from controllers.spotify.spotify_browser import SpotifyBrowser
from controllers.spotify.spotify_account import SpotifyAccountController, SpotifyAccountBinding, Current, Commit
from controllers.spotify.guarded_token_store import GuardedTokenStore
from frontends.tk.media.spotify_account_dialog import SpotifyAccountDialog
from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.video import MusicVideoController, NetflixPlayer, YouTubeMusicVideo, YouTubePlayer
from frontends.x11 import X11WindowEmbedder
from frontends.tk.media import BrowserMediaScreen, MediaNavigationBar, MediaScreen, SpotifyNowPlaying, SpotifyScreen
from frontends.tk.media.youtube_music_coming_soon_screen import YouTubeMusicComingSoonScreen
from ui.theme import ThemeMode
from protocols.spotify import (
    SPOTIFY_CLIENT_ID_SECRET_NAME,
    SpotifyAuth,
    SpotifyTokenStore,
    load_spotify_config_from_secrets,
)
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager

MUSIC_VIDEO_PORT = 8770
MUSIC_VIDEO_WINDOW_CLASS = "OpenRoadCodeMusicVideo"
YOUTUBE_WINDOW_CLASS = "openroadcode-youtube"
YOUTUBE_MUSIC_WINDOW_CLASS = "openroadcode-youtube-music"
NETFLIX_WINDOW_CLASS = "openroadcode-netflix"
SPOTIFY_GREEN = "#1DB954"


@dataclass(slots=True)
class MediaComposition:
    music_video_controller: MusicVideoController
    home_factory: Callable[[tk.Misc], tk.Widget]
    visualizer: MusicVisualizerScreen | BrowserMediaScreen
    visualizer_runtime: MusicVisualizerController | MusicVisualizerBrowser
    unsubscribe_online: Callable[[], None] = lambda: None
    close_spotify_presentations: Callable[[], None] = lambda: None
    close_spotify_accounts: Callable[[], None] = lambda: None

    _closed: bool = field(default=False, init=False)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        close_resources(self.unsubscribe_online, self.close_spotify_accounts, self.close_spotify_presentations, self.visualizer.hide,
                        self.visualizer_runtime.close, self.music_video_controller.stop_video)


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
    with ResourceCleanup() as cleanup:
        composition = _configure_media(app, runtime, cleanup)
        cleanup.release()
        return composition


def _configure_media(app: OrcUiApp, runtime, cleanup: ResourceCleanup) -> MediaComposition:
    media = runtime.media
    network_allowed = lambda: app.online_mode.online
    media.spotify.set_network_allowed(network_allowed)
    media.spotify_local_player.set_network_allowed(network_allowed)
    def online_action(action):
        def invoke():
            if not network_allowed():
                app.set_screen_status("Offline mode: online media unavailable")
                return
            return action()
        return invoke

    software_rendering = detect_runtime_target() is RuntimeTarget.LINUX_DEV
    image_cache = ImageCache(max_entries=128, cache_directory=openroadcode_cache_dir("media-art"))
    lyrics = LrclibLyricsClient()
    music_video = YouTubeMusicVideo(
        port=MUSIC_VIDEO_PORT, fullscreen=False, software_rendering=software_rendering,
        window_class=MUSIC_VIDEO_WINDOW_CLASS, show_return_button=False,
    )
    music_video_controller = MusicVideoController(spotify_controller=media.spotify.controller, music_video=music_video, network_allowed=network_allowed)

    cleanup.callback(music_video_controller.stop_video)

    def media_navigation(parent, active: str):
        return MediaNavigationBar(
            parent, theme_bundle=lambda: theme_bundle(app.theme_mode), active=active,
            show_media=lambda: media_screen.show(), show_home=lambda: app.navigate_to("HOME"),
            show_spotify=online_action(lambda: spotify_screen.show()), show_youtube=online_action(lambda: youtube_screen.show()),
            show_netflix=online_action(lambda: netflix_screen.show()),
        )

    browser_color_scheme = lambda: "dark" if app.theme_mode is ThemeMode.DARK else "light"
    youtube_player = ManagedBrowserMediaPlayer(
        runtime.manager, "youtube", resolve_target=YouTubePlayer.resolve_target,
        preferred_color_scheme=browser_color_scheme,
        network_allowed=network_allowed,
    )
    netflix_player = ManagedBrowserMediaPlayer(
        runtime.manager, "netflix", resolve_target=NetflixPlayer.validate_url,
        preferred_color_scheme=browser_color_scheme,
        network_allowed=network_allowed,
    )
    youtube_screen = BrowserMediaScreen(
        "youtube", app, title="YouTube", player=youtube_player,
        default_target="https://www.youtube.com/", window_class=YOUTUBE_WINDOW_CLASS,
        back_action=lambda: media_screen.show(), media_navigation_factory=media_navigation,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )
    youtube_music_screen = YouTubeMusicComingSoonScreen(
        app,
        back_action=lambda: media_screen.show(),
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )
    netflix_screen = BrowserMediaScreen(
        "netflix", app, title="Netflix", player=netflix_player,
        default_target="https://www.netflix.com/browse", window_class=NETFLIX_WINDOW_CLASS,
        back_action=lambda: media_screen.show(), media_navigation_factory=media_navigation,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )

    def show_spotify_remote() -> None:
        if not network_allowed():
            return
        media.spotify_local_player.request_remote()
        media.spotify.request_refresh()
        spotify_screen.show()

    def show_spotify_local() -> None:
        if not network_allowed():
            return
        media.spotify_local_player.request_player()
        spotify_screen.show()

    spotify_secrets = EnvironmentVariableSecretManager()

    def spotify_client_id() -> str | None:
        return EnvironmentVariableSecretManager().get_secret(SPOTIFY_CLIENT_ID_SECRET_NAME)

    spotify_tokens = SpotifyTokenStore()
    account_workers = ThreadPoolExecutor(max_workers=2, thread_name_prefix="spotify-account")
    cleanup.callback(lambda: account_workers.shutdown(wait=False, cancel_futures=True))

    def connect_spotify(current: Current, commit: Commit) -> None:
        config = load_spotify_config_from_secrets(EnvironmentVariableSecretManager())
        if config is None:
            raise RuntimeError("Configure the Spotify Client ID first")
        SpotifyAuth(config=config, token_store=GuardedTokenStore(spotify_tokens, commit)).login(is_current=current)

    account_controller = SpotifyAccountController(
        read_account=lambda: (spotify_client_id() or "", spotify_tokens.load() is not None),
        save_client_id=lambda client_id: spotify_secrets.set_secret(SPOTIFY_CLIENT_ID_SECRET_NAME, client_id),
        connect=connect_spotify, disconnect=spotify_tokens.clear, online=network_allowed,
        run_work=lambda callback: account_workers.submit(callback), dispatcher=app,
        refresh_playback=media.spotify.request_refresh,
    )
    cleanup.callback(account_controller.close)
    media_account = SpotifyAccountBinding(account_controller)
    playback_account = SpotifyAccountBinding(account_controller)
    dialog_account = SpotifyAccountBinding(account_controller)
    account_dialog = SpotifyAccountDialog(
        app.screen_parent, session=dialog_account, theme_bundle=lambda: theme_bundle(app.theme_mode),
    )

    def close_accounts() -> None:
        try:
            close_resources(account_controller.close, account_dialog.close,
                            media_account.close, playback_account.close, dialog_account.close)
        finally:
            account_workers.shutdown(wait=False, cancel_futures=True)

    cleanup.callback(close_accounts)

    presentation_workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="spotify-presentation")
    cleanup.callback(lambda: presentation_workers.shutdown(wait=False, cancel_futures=True))
    presentations: list[SpotifyPresentation] = []
    browsers: list[SpotifyBrowser] = []
    retire_views: list[Callable[[], None]] = []

    def create_presentation(*, rich: bool) -> SpotifyPresentation:
        session = create_spotify_presentation(
            media.spotify, image_cache, lyrics, music_video_controller, app,
            presentation_workers, online=network_allowed, rich=rich,
            process_id=lambda: music_video.browser_process_id,
        )
        presentations.append(session)
        return session

    def close_presentations() -> None:
        try:
            close_resources(*retire_views, *(session.close for session in presentations),
                            *(browser.close for browser in browsers))
        finally:
            presentation_workers.shutdown(wait=False, cancel_futures=True)

    cleanup.callback(close_presentations)
    playback_session = create_presentation(rich=True)

    browser_session = SpotifyBrowser(
        media.spotify, media.spotify_local_player,
        run_work=lambda callback: presentation_workers.submit(callback), dispatcher=app,
        load_artwork=cached_artwork_loader(image_cache, max_size=56), online=network_allowed,
        show_now_playing=lambda: spotify_screen.show(),
    )
    browsers.append(browser_session)
    spotify_screen = SpotifyScreen(
        app, theme=lambda: spotify_theme(app), back_action=lambda: media_screen.show(),
        playback_session=playback_session, native_surface=X11WindowEmbedder(),
        browse_session=browser_session, media_navigation_factory=media_navigation,
        account_session=playback_account,
        show_account_configuration=account_dialog.show,
        close_account_configuration=account_dialog.close,
    )
    retire_views.append(spotify_screen.hide)

    if os.getenv("OPENROAD_MUSIC_VISUALIZER_RENDERER", "webgl").lower() == "tk":
        visualizer_runtime = MusicVisualizerController(create_music_visualizer_session)
        cleanup.callback(visualizer_runtime.close)
        visualizer = MusicVisualizerScreen(
            app, on_back=lambda: media_screen.show(), controller=visualizer_runtime,
            initial_source=selected_music_visualizer_source(),
            theme_bundle=lambda: theme_bundle(app.theme_mode),
        )
    else:
        visualizer_runtime = create_browser_visualizer(app)
        cleanup.callback(visualizer_runtime.close)
        visualizer = BrowserMediaScreen(
            "music-visualizer", app, title="Music Visualizer", player=visualizer_runtime,
            default_target=visualizer_runtime.url, window_class=WINDOW_CLASS,
            back_action=lambda: media_screen.show(), media_navigation_factory=media_navigation,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
        )
    cleanup.callback(visualizer.hide)
    app.register_screen("VISUALIZER", visualizer, show_in_navigation=False)
    media_screen = MediaScreen(
        app, theme_bundle=lambda: theme_bundle(app.theme_mode),
        online_allowed=network_allowed,
        show_spotify=spotify_screen.show, show_youtube=youtube_screen.show,
        show_youtube_music=youtube_music_screen.show, show_netflix=netflix_screen.show,
        show_visualizer=visualizer.show,
        show_spotify_remote=show_spotify_remote, show_spotify_local=show_spotify_local,
        spotify_local_available=lambda: media.spotify_local_player.state().available,
        account_session=media_account,
        show_account_configuration=account_dialog.show,
        close_account_configuration=account_dialog.close,
    )
    app.register_screen("MEDIA", media_screen)

    def home_media_factory(parent: tk.Misc) -> tk.Widget:
        view = SpotifyNowPlaying(
            parent,
            online_allowed=network_allowed,
            on_open=online_action(spotify_screen.show),
            theme_bundle=lambda: theme_bundle(app.theme_mode),
        )
        session = create_presentation(rich=False)
        def retire(event: tk.Event) -> None:
            if event.widget is view:
                session.close()
                if session in presentations:
                    presentations.remove(session)
        view.bind("<Destroy>", retire, add="+")
        session.activate(view)
        return view

    def mode_changed(online: bool) -> None:
        account_controller.network_changed()
        if not online:
            for stop in (music_video_controller.stop_video, youtube_player.stop,
                         netflix_player.stop, media.spotify_local_player.request_remote):
                try:
                    stop()
                except (OSError, RuntimeError) as exc:
                    app.set_screen_status(f"Could not stop online media: {exc}")
            if getattr(app, "_active_screen", None) in (
                spotify_screen, youtube_screen, netflix_screen, youtube_music_screen,
            ):
                media_screen.show()
        if getattr(app, "_active_screen", None) is media_screen:
            media_screen.show()
    unsubscribe_online = app.online_mode.subscribe(mode_changed)
    cleanup.callback(unsubscribe_online)
    mode_changed(app.online_mode.online)

    return MediaComposition(
        music_video_controller=music_video_controller,
        home_factory=home_media_factory,
        visualizer=visualizer,
        visualizer_runtime=visualizer_runtime,
        unsubscribe_online=unsubscribe_online,
        close_spotify_presentations=close_presentations,
        close_spotify_accounts=close_accounts,
    )
