# SPDX-License-Identifier: MIT

"""Keep the shared Spotify screen's legacy Car UI caller on contract wiring."""

from concurrent.futures import ThreadPoolExecutor

from apps.carUi.car_ui_dependencies import CarUiDependencies
from apps.common.spotify_presentation_factory import create_spotify_presentation
from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from common.resource_cleanup import ResourceCleanup, close_resources
from controllers.audio import MediaVolumeHandler
from controllers.spotify.spotify_state_service import SpotifyStateService
from frontends.tk.media import SpotifyScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from frontends.x11 import X11WindowEmbedder
from collections.abc import Callable


def create_spotify_screen(host: TkScreenHostIf, dependencies: CarUiDependencies, back: Callable[[], None]) -> SpotifyScreen:
    with ResourceCleanup() as cleanup:
        service = SpotifyStateService(dependencies.spotify_controller,
            fallback_volume_handler=MediaVolumeHandler(dependencies.audio_controller))
        cleanup.callback(service.close)
        workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="carui-spotify")
        cleanup.callback(lambda: workers.shutdown(wait=False, cancel_futures=True))
        session = create_spotify_presentation(service, dependencies.spotify_image_cache,
            dependencies.spotify_lyrics_client, dependencies.spotify_music_video_controller, host, workers)
        cleanup.callback(session.close)
        screen = SpotifyScreen(host, theme=SPOTIFY_PANEL_THEME, back_action=back,
            playback_session=session, native_surface=X11WindowEmbedder())
        cleanup.callback(screen.hide)
        service.start()
        def close() -> None:
            try:
                close_resources(screen.hide, session.close, service.close)
            finally:
                workers.shutdown(wait=False, cancel_futures=True)
        dependencies.presentation_cleanup.append(close)
        cleanup.release()
    return screen
