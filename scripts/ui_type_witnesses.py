# SPDX-License-Identifier: MIT

"""Static binding checks for structural UI protocols; never construct resources."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
    from frontends.tk.tk_screen_host_if import TkScreenHostIf
    from ui.ui_dispatcher_if import UiDispatcherIf

    def shell_dispatcher(shell: OrcUiApp) -> UiDispatcherIf:
        return shell

    def shell_screen_host(shell: OrcUiApp) -> TkScreenHostIf:
        return shell

    from controllers.games.games_session import GamesSession
    from frontends.tk.games.games_screen import GamesScreen
    from frontends.x11.x11_window_embedder import X11WindowEmbedder
    from ui.games.games_session_if import GamesSessionIf, GamesRuntimeUiIf
    from ui.games.game_window_embedder_if import GameWindowEmbedderIf

    def games_session(session: GamesSession) -> GamesSessionIf:
        return session

    def games_surface(screen: GamesScreen) -> GamesRuntimeUiIf:
        return screen

    def games_embedder(adapter: X11WindowEmbedder) -> GameWindowEmbedderIf:
        return adapter

    from controllers.radio.streaming_radio_browser import StreamingRadioBrowser
    from controllers.radio.streaming_radio_controller import StreamingRadioController
    from controllers.radio.streaming_radio_favorites import StreamingRadioFavorites
    from controllers.radio.streaming_radio_backend_if import StreamingRadioBackendIf, StreamingRadioFavoritesIf
    from frontends.tk.radio.streaming_radio_panel import StreamingRadioPanel
    from ui.radio.streaming_radio_session_if import StreamingRadioSessionIf, StreamingRadioUiIf
    from ui.radio.streaming_radio_state_source_if import StreamingRadioStateSourceIf

    def radio_session(session: StreamingRadioBrowser) -> StreamingRadioSessionIf:
        return session

    def radio_browser(view: StreamingRadioPanel) -> StreamingRadioUiIf:
        return view

    def radio_summary(source: StreamingRadioController) -> StreamingRadioStateSourceIf:
        return source

    def radio_backend(backend: StreamingRadioController) -> StreamingRadioBackendIf:
        return backend

    def radio_favorites(storage: StreamingRadioFavorites) -> StreamingRadioFavoritesIf:
        return storage

    from controllers.radio.rf_radio_session import ReceiverSession
    from apps.orcUi.frontend.tk.radio_panel import RadioPanel
    from ui.radio.rf_radio_if import RfRadioSession, RfRadioUi, RadioNativeSurface

    def rf_session(session: ReceiverSession) -> RfRadioSession:
        return session

    def rf_view(view: RadioPanel) -> RfRadioUi:
        return view

    def rf_surface(adapter: X11WindowEmbedder) -> RadioNativeSurface:
        return adapter

    from controllers.spotify.spotify_presentation import SpotifyPresentation
    from frontends.tk.media.spotify_now_playing import SpotifyNowPlaying
    from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel
    from ui.media.spotify_presentation_if import SpotifyPresentationSession, SpotifyPresentationUi
    from ui.media import VolumeRequestHandlerIf

    def spotify_session(session: SpotifyPresentation) -> SpotifyPresentationSession:
        return session

    def spotify_summary(view: SpotifyNowPlaying) -> SpotifyPresentationUi:
        return view

    def spotify_panel(view: SpotifyPlaybackPanel) -> SpotifyPresentationUi:
        return view

    def spotify_volume(session: SpotifyPresentation) -> VolumeRequestHandlerIf:
        return session

    from controllers.spotify.spotify_browser import SpotifyBrowser
    from frontends.tk.media.spotify_browse_panel import SpotifyBrowsePanel
    from frontends.tk.media.spotify_screen import SpotifyScreen
    from ui.media.spotify_browse_if import SpotifyBrowseSession, SpotifyBrowseUi
    from ui.media.spotify_presentation_if import SpotifyNativeSurface

    def spotify_browser_session(session: SpotifyBrowser) -> SpotifyBrowseSession:
        return session

    def spotify_browser_view(view: SpotifyBrowsePanel) -> SpotifyBrowseUi:
        return view

    def spotify_screen_view(view: SpotifyScreen) -> SpotifyPresentationUi:
        return view

    def spotify_native_surface(adapter: X11WindowEmbedder) -> SpotifyNativeSurface:
        return adapter

if TYPE_CHECKING:
    from controllers.spotify.spotify_account import SpotifyAccountBinding
    from frontends.tk.media.media_screen import MediaScreen
    from frontends.tk.media.spotify_account_dialog import SpotifyAccountDialog
    from ui.media.spotify_account_if import SpotifyAccountSession, SpotifyAccountUi

    def spotify_account_session(session: SpotifyAccountBinding) -> SpotifyAccountSession:
        return session

    def spotify_account_media(view: MediaScreen) -> SpotifyAccountUi:
        return view

    def spotify_account_screen(view: SpotifyScreen) -> SpotifyAccountUi:
        return view

    def spotify_account_dialog(view: SpotifyAccountDialog) -> SpotifyAccountUi:
        return view
