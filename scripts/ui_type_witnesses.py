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
