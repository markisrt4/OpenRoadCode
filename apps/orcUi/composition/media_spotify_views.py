"""Compose Home and Trending views from shared Spotify playback sessions."""

import os
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.frontend.tk.trending_spotify_pane import build_trending_spotify_pane
from controllers.spotify.spotify_presentation import SpotifyPresentation
from frontends.tk.media import SpotifyNowPlaying
from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel
from ui.media.spotify_browse_if import SpotifyLocalPlayerState
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
    report_status: Callable[[str], None],
    dispatch_ui: Callable[[Callable[[], None]], None],
    request_song: Callable[[str, str, Callable[[str], None]], None],
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
            report_status=report_status,
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
