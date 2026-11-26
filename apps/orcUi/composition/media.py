# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Compose media screens, services, and presentation resources."""

from __future__ import annotations

import io
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from apps.common.spotify_presentation_factory import (
    cached_artwork_loader,
    create_spotify_presentation,
)
from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
from apps.orcUi.adapters.music_visualizer_browser import WINDOW_CLASS
from apps.orcUi.composition.music_visualizer import (
    create_browser_visualizer,
    create_music_visualizer_session,
    home_spectrum_factory,
    selected_native_visualizer_source,
)
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from common.resource_cleanup import ResourceCleanup, close_resources
from common.xdg_paths import openroadcode_cache_dir
from config.runtime_target import RuntimeTarget, detect_runtime_target
from controllers.audio.music_analysis.music_visualizer_controller import MusicVisualizerController
from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.media.song_launch_controller import SongLaunchController
from controllers.spotify.guarded_token_store import GuardedTokenStore
from controllers.spotify.media_preview_controller import MediaPreviewController
from controllers.spotify.spotify_account import (
    Commit,
    Current,
    SpotifyAccountBinding,
    SpotifyAccountController,
)
from controllers.spotify.spotify_browser import SpotifyBrowser
from controllers.spotify.spotify_presentation import SpotifyPresentation
from controllers.video import MusicVideoController, NetflixPlayer, YouTubeMusicVideo, YouTubePlayer
from frontends.tk.media import (
    BrowserMediaScreen,
    MediaNavigationBar,
    MediaScreen,
    SpotifyScreen,
)
from frontends.tk.media.music_visualizer_screen import MusicVisualizerScreen
from frontends.tk.media.spotify_account_dialog import SpotifyAccountDialog
from frontends.tk.media.youtube_music_coming_soon_screen import YouTubeMusicComingSoonScreen
from frontends.x11 import X11WindowEmbedder
from protocols.spotify import (
    SPOTIFY_CLIENT_ID_SECRET_NAME,
    SpotifyAuth,
    SpotifyTokenStore,
    load_spotify_config_from_secrets,
)
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager
from ui.music_visualizer import MusicVisualizerSource
from ui.notification_if import Notification, NotificationSeverity
from ui.theme import ThemeMode

from .media_resources import MediaComposition
from .media_spotify_theme import SPOTIFY_GREEN as SPOTIFY_GREEN
from .media_spotify_theme import spotify_theme as spotify_theme
from .media_spotify_views import bind_spotify_views

MUSIC_VIDEO_PORT = 8770
MUSIC_VIDEO_WINDOW_CLASS = "OpenRoadCodeMusicVideo"
YOUTUBE_WINDOW_CLASS = "openroadcode-youtube"
YOUTUBE_MUSIC_WINDOW_CLASS = "openroadcode-youtube-music"
NETFLIX_WINDOW_CLASS = "openroadcode-netflix"


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

    def preview_artwork(url):
        image = image_cache.get(url, width=56, height=56)
        try:
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
        finally:
            image.close()

    preview = MediaPreviewController(
        media.spotify.latest_state, preview_artwork, online_allowed=network_allowed
    )
    cleanup.callback(preview.close)
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
        network_allowed=network_allowed,
    )

    cleanup.callback(music_video_controller.stop_video)

    def media_navigation(parent, active: str):
        return MediaNavigationBar(
            parent,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            active=active,
            show_media=lambda: media_screen.show(),
            show_home=lambda: app.navigate_to("HOME"),
            show_spotify=show_spotify,
            show_youtube=online_action(lambda: youtube_screen.show()),
            show_netflix=online_action(lambda: netflix_screen.show()),
        )

    browser_color_scheme = lambda: "dark" if app.theme_mode is ThemeMode.DARK else "light"
    youtube_player = ManagedBrowserMediaPlayer(
        runtime.manager,
        "youtube",
        resolve_target=YouTubePlayer.resolve_target,
        preferred_color_scheme=browser_color_scheme,
        network_allowed=network_allowed,
    )
    netflix_player = ManagedBrowserMediaPlayer(
        runtime.manager,
        "netflix",
        resolve_target=NetflixPlayer.validate_url,
        preferred_color_scheme=browser_color_scheme,
        network_allowed=network_allowed,
    )
    youtube_screen = BrowserMediaScreen(
        "youtube",
        app,
        title="YouTube",
        player=youtube_player,
        default_target="https://www.youtube.com/",
        window_class=YOUTUBE_WINDOW_CLASS,
        back_action=lambda: media_screen.show(),
        media_navigation_factory=media_navigation,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )
    song_launch_controller = SongLaunchController(
        open_spotify_search=lambda query: online_action(lambda: open_trending_spotify(query))(),
        open_youtube_search=lambda query: online_action(
            lambda: youtube_screen.show_target(query)
        )(),
    )
    youtube_music_screen = YouTubeMusicComingSoonScreen(
        app,
        back_action=lambda: media_screen.show(),
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )
    netflix_screen = BrowserMediaScreen(
        "netflix",
        app,
        title="Netflix",
        player=netflix_player,
        default_target="https://www.netflix.com/browse",
        window_class=NETFLIX_WINDOW_CLASS,
        back_action=lambda: media_screen.show(),
        media_navigation_factory=media_navigation,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )

    def show_spotify() -> None:
        if not network_allowed():
            return
        spotify_screen.show()
        if not spotify_client_id():
            app.notification_sink.publish(
                Notification(
                    code="spotify.configuration_required",
                    title="Spotify configuration required",
                    message="Open Settings > Media > Spotify to enter your application Client ID.",
                    severity=NotificationSeverity.WARNING,
                    source="spotify",
                )
            )

    def open_trending_spotify(query: str) -> None:
        """Keep MusicForge handoff inside ORC's native Spotify screen."""
        show_spotify()
        app.set_screen_status(
            f"Spotify opened for {query}. Automatic track lookup is not available yet."
        )

    def show_spotify_remote() -> None:
        if not network_allowed():
            return
        media.spotify_local_player.request_remote()
        media.spotify.request_refresh()
        show_spotify()

    def show_spotify_local() -> None:
        if not network_allowed():
            return
        if not spotify_client_id():
            show_spotify()
            return
        media.spotify_local_player.request_player()
        show_spotify()

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
        SpotifyAuth(config=config, token_store=GuardedTokenStore(spotify_tokens, commit)).login(
            is_current=current
        )

    account_controller = SpotifyAccountController(
        read_account=lambda: (spotify_client_id() or "", spotify_tokens.load() is not None),
        save_client_id=lambda client_id: spotify_secrets.set_secret(
            SPOTIFY_CLIENT_ID_SECRET_NAME, client_id
        ),
        connect=connect_spotify,
        disconnect=spotify_tokens.clear,
        online=network_allowed,
        run_work=lambda callback: account_workers.submit(callback),
        dispatcher=app,
        refresh_playback=media.spotify.request_refresh,
    )
    cleanup.callback(account_controller.close)
    media_account = SpotifyAccountBinding(account_controller)
    playback_account = SpotifyAccountBinding(account_controller)
    dialog_account = SpotifyAccountBinding(account_controller)
    account_dialog = SpotifyAccountDialog(
        app.screen_parent,
        session=dialog_account,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )

    def close_accounts() -> None:
        try:
            close_resources(
                account_controller.close,
                account_dialog.close,
                media_account.close,
                playback_account.close,
                dialog_account.close,
            )
        finally:
            account_workers.shutdown(wait=False, cancel_futures=True)

    cleanup.callback(close_accounts)

    presentation_workers = ThreadPoolExecutor(
        max_workers=4, thread_name_prefix="spotify-presentation"
    )
    cleanup.callback(lambda: presentation_workers.shutdown(wait=False, cancel_futures=True))
    presentations: list[SpotifyPresentation] = []
    browsers: list[SpotifyBrowser] = []
    retire_views: list[Callable[[], None]] = []

    def create_presentation(*, rich: bool) -> SpotifyPresentation:
        session = create_spotify_presentation(
            media.spotify,
            image_cache,
            lyrics,
            music_video_controller,
            app,
            presentation_workers,
            online=network_allowed,
            rich=rich,
            process_id=lambda: music_video.browser_process_id,
        )
        presentations.append(session)
        return session

    def close_presentations() -> None:
        try:
            close_resources(
                *retire_views,
                *(session.close for session in presentations),
                *(browser.close for browser in browsers),
            )
        finally:
            presentation_workers.shutdown(wait=False, cancel_futures=True)

    cleanup.callback(close_presentations)
    playback_session = create_presentation(rich=True)

    browser_session = SpotifyBrowser(
        media.spotify,
        media.spotify_local_player,
        run_work=lambda callback: presentation_workers.submit(callback),
        dispatcher=app,
        load_artwork=cached_artwork_loader(image_cache, max_size=56),
        online=network_allowed,
        show_now_playing=show_spotify,
    )
    browsers.append(browser_session)
    spotify_screen = SpotifyScreen(
        app,
        theme=lambda: spotify_theme(app),
        back_action=lambda: media_screen.show(),
        show_visualizer=lambda: visualizer.show(),
        playback_session=playback_session,
        native_surface=X11WindowEmbedder(),
        browse_session=browser_session,
        media_navigation_factory=media_navigation,
        account_session=playback_account,
        show_account_configuration=account_dialog.show,
        close_account_configuration=account_dialog.close,
    )
    retire_views.append(spotify_screen.hide)

    renderer = os.getenv("OPENROAD_MUSIC_VISUALIZER_RENDERER", "opengl").lower()
    if renderer in {"tk", "opengl"}:
        panel_options = {}
        if renderer == "opengl":
            from functools import partial

            from apps.orcUi.frontend.tk.ecu_gl_backend import load_gl_backend
            from frontends.tk.media.native_music_visualizer import NativeMusicVisualizerPanel

            panel_options["panel_factory"] = partial(
                NativeMusicVisualizerPanel, gl_backend=load_gl_backend
            )
        visualizer_runtime = MusicVisualizerController(create_music_visualizer_session)
        cleanup.callback(visualizer_runtime.close)
        visualizer = MusicVisualizerScreen(
            app,
            on_back=lambda: media_screen.show(),
            controller=visualizer_runtime,
            initial_source=selected_native_visualizer_source(),
            native_controls=renderer == "opengl",
            share_session=renderer == "opengl",
            **panel_options,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
        )
    else:
        visualizer_runtime = create_browser_visualizer(app)
        cleanup.callback(visualizer_runtime.close)
        visualizer = BrowserMediaScreen(
            "music-visualizer",
            app,
            title="Music Visualizer",
            player=visualizer_runtime,
            default_target=visualizer_runtime.url,
            window_class=WINDOW_CLASS,
            back_action=lambda: media_screen.show(),
            media_navigation_factory=media_navigation,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
        )
    cleanup.callback(visualizer.hide)
    app.register_screen("VISUALIZER", visualizer, show_in_navigation=False)
    media_screen = MediaScreen(
        app,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
        preview=preview,
        online_allowed=network_allowed,
        show_spotify=show_spotify,
        show_youtube=youtube_screen.show,
        show_youtube_music=youtube_music_screen.show,
        show_netflix=netflix_screen.show,
        show_visualizer=visualizer.show,
        show_spotify_remote=show_spotify_remote,
        show_spotify_local=show_spotify_local,
        spotify_local_available=lambda: media.spotify_local_player.state().available,
        account_session=media_account,
        close_account_configuration=account_dialog.close,
    )
    app.register_screen("MEDIA", media_screen)

    home_capture_attached = False

    def home_playback_changed(playing: bool) -> None:
        """Share native audio capture with other views without stopping their session."""
        nonlocal home_capture_attached
        if not isinstance(visualizer_runtime, MusicVisualizerController):
            return
        source = selected_native_visualizer_source()
        if source is MusicVisualizerSource.SIMULATED:
            return  # Idle animation is not a measured spectrum.
        if playing and not home_capture_attached:
            home_capture_attached = True
            visualizer_runtime.attach_view("home-playback")
            if visualizer_runtime.capture_state().value == "idle":
                visualizer_runtime.start(source)
        elif not playing and home_capture_attached:
            home_capture_attached = False
            visualizer_runtime.detach_view("home-playback")

    home_now_playing_factory, trending_spotify_factory = bind_spotify_views(
        create_presentation=lambda: create_presentation(rich=True),
        presentations=presentations,
        network_allowed=network_allowed,
        home_theme=lambda: theme_bundle(app.theme_mode),
        open_spotify=show_spotify,
        home_playback_changed=home_playback_changed,
        spotify_colors=lambda: spotify_theme(app),
        show_error=app.show_error,
        dispatch_ui=app.dispatch_ui,
        request_song=media.spotify.request_play_song,
        player_state=media.spotify_local_player.state,
        request_player=media.spotify_local_player.request_player,
        spotify_configured=lambda: bool(spotify_client_id()),
    )

    def mode_changed(online: bool) -> None:
        account_controller.network_changed()
        if not online:
            for stop in (
                music_video_controller.stop_video,
                youtube_player.stop,
                netflix_player.stop,
                media.spotify_local_player.request_remote,
            ):
                try:
                    stop()
                except (OSError, RuntimeError) as exc:
                    app.set_screen_status(f"Could not stop online media: {exc}")
            if getattr(app, "_active_screen", None) in (
                spotify_screen,
                youtube_screen,
                netflix_screen,
                youtube_music_screen,
            ):
                media_screen.show()
        if getattr(app, "_active_screen", None) is media_screen:
            media_screen.show()

    unsubscribe_online = app.online_mode.subscribe(mode_changed)
    cleanup.callback(unsubscribe_online)
    mode_changed(app.online_mode.online)

    return MediaComposition(
        preview=preview,
        music_video_controller=music_video_controller,
        song_launch_controller=song_launch_controller,
        trending_youtube_player=youtube_player,
        trending_spotify_factory=trending_spotify_factory,
        home_factory=home_now_playing_factory,
        home_visualizer_factory=home_spectrum_factory(
            lambda: theme_bundle(app.theme_mode), visualizer_runtime, visualizer.show
        )
        if renderer == "opengl"
        else None,
        visualizer=visualizer,
        visualizer_runtime=visualizer_runtime,
        unsubscribe_online=unsubscribe_online,
        close_spotify_presentations=close_presentations,
        close_spotify_accounts=close_accounts,
        configure_spotify=account_dialog.show,
        close_spotify_configuration=account_dialog.close,
    )
