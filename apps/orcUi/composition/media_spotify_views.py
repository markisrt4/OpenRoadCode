"""Compose Home and Trending views from shared Spotify playback sessions."""

import os
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.trending_spotify_pane import build_trending_spotify_pane
from controllers.spotify.spotify_presentation import SpotifyPresentation
from frontends.tk.media import SpotifyNowPlaying
from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel
from ui.media.spotify_browse_if import SpotifyLocalPlayerState, SpotifyPlaybackMode
from ui.theme import ThemeBundle

SpotifyFactory = Callable[[tk.Misc, Callable[[], None], str, str], tk.Widget]


def bind_spotify_views(
    *,
    create_presentation: Callable[[], SpotifyPresentation],
    presentations: list[SpotifyPresentation],
    network_allowed: Callable[[], bool],
    home_theme: Callable[[], ThemeBundle],
    open_spotify: Callable[[], None],
    home_playback_changed: Callable[[bool], None],
    spotify_colors: Callable[[], dict],
    show_error: Callable[[str, str], None],
    dispatch_ui: Callable[[Callable[[], None]], None],
    request_song: Callable[[str, str, Callable[[str], None], Callable[[str], None]], None],
    player_state: Callable[[], SpotifyLocalPlayerState],
    request_player: Callable[[], None],
    spotify_configured: Callable[[], bool],
) -> tuple[Callable[[tk.Misc], tk.Widget], SpotifyFactory]:
    android = bool(
        os.environ.get("TERMUX_VERSION")
        or os.environ.get("TERMUX__PREFIX")
        or os.environ.get("PREFIX", "").startswith("/data/data/com.termux/")
    )

    def home_now_playing_factory(parent: tk.Misc) -> tk.Widget:
        view = SpotifyNowPlaying(
            parent,
            online_allowed=network_allowed,
            on_open=open_spotify,
            theme_bundle=home_theme,
            on_playback_changed=home_playback_changed,
        )
        session = create_presentation()

        def retire(event: tk.Event) -> None:
            if event.widget is view:
                home_playback_changed(False)
                session.close()
                if session in presentations:
                    presentations.remove(session)

        view.bind("<Destroy>", retire, add="+")
        session.activate(view)
        return view

    def activate_trending(panel: SpotifyPlaybackPanel) -> Callable[[], None]:
        session = create_presentation()
        session.activate(panel)

        def retire() -> None:
            session.close()
            if session in presentations:
                presentations.remove(session)

        return retire

    def trending_spotify_factory(
        parent: tk.Misc,
        on_back: Callable[[], None],
        artist: str,
        title: str,
    ) -> tk.Widget:
        return build_trending_spotify_pane(
            parent,
            on_back,
            artist,
            title,
            theme=spotify_colors(),
            activate=activate_trending,
            show_error=show_error,
            dispatch_ui=dispatch_ui,
            android=android,
            network_allowed=network_allowed,
            request_song=request_song,
            player_state=player_state,
            request_player=request_player,
            configured=spotify_configured(),
            on_setup=open_spotify,
        )

    return home_now_playing_factory, trending_spotify_factory


def verify_spotify_local_player(
    app: OrcUiApp,
    player_state: Callable[[], SpotifyLocalPlayerState],
    request_player: Callable[[], None],
    network_allowed: Callable[[], bool],
) -> None:
    """Start the local player and show the result of device registration."""
    request_player()

    def report_result() -> None:
        if not network_allowed():
            return
        state = player_state()
        if state.busy:
            app.schedule_ui_callback(200, report_result)
        elif state.mode is SpotifyPlaybackMode.PLAYER:
            app.set_screen_status("Spotify local player ready. Open Radio → Trending to test a song.")
        else:
            app.show_error("Spotify local player test failed", state.message)

    report_result()
