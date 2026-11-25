"""Composition wiring for Trending charts and playback."""

import os
import tkinter as tk
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
from apps.orcUi.adapters.musicforge_api_adapter import MusicForgeApiAdapter
from apps.orcUi.adapters.trending_video_session import ManagedTrendingVideoSession
from apps.orcUi.frontend.tk.trending_radio_panel import TrendingRadioPanel
from common.xdg_paths import openroadcode_cache_dir
from controllers.cache.persistent_cache import PersistentCache
from controllers.media.artist_profiles import ArtistProfiles
from ui.media.song_launch import SongDestination, SongLaunchRequest
from ui.media.trending_video import TrendingVideoSession
from ui.notification_if import Notification, NotificationSeverity, NotificationSinkIf
from ui.theme import ThemeBundle

SpotifyFactory = Callable[[tk.Misc, Callable[[], None], str, str], tk.Widget]


@dataclass(frozen=True, slots=True)
class TrendingBindings:
    panel_factory: Callable[[tk.Misc, ThemeBundle, Callable[[], None]], TrendingRadioPanel]
    bind_song_launch: Callable[[Callable[[SongLaunchRequest], None]], None]
    bind_video_player: Callable[[ManagedBrowserMediaPlayer], None]
    bind_spotify_factory: Callable[[SpotifyFactory], None]
    close_charts: Callable[[], None]


def configure_trending(
    *,
    register_cleanup: Callable[[Callable[[], None]], object],
    dispatch_ui: Callable[[Callable[[], None]], None],
    run_work: Callable[[Callable[[], None]], None],
    network_allowed: Callable[[], bool],
    closed: Callable[[], bool],
    notification_sink: NotificationSinkIf,
) -> TrendingBindings:
    charts = MusicForgeApiAdapter(os.getenv("MUSICFORGE_AIRPLAY_URL", "http://127.0.0.1:8000"))
    register_cleanup(charts.close)
    profiles = ArtistProfiles(PersistentCache(openroadcode_cache_dir("artist-profiles")))
    song_launch: list[Callable[[SongLaunchRequest], None]] = []
    video_players: list[ManagedBrowserMediaPlayer] = []
    spotify_factories: list[Callable[[tk.Misc, Callable[[], None], str, str], tk.Widget]] = []

    def bind_spotify_factory(
        factory: Callable[[tk.Misc, Callable[[], None], str, str], tk.Widget],
    ) -> None:
        spotify_factories[:] = [factory]

    def bind_video_player(player: ManagedBrowserMediaPlayer) -> None:
        video_players[:] = [player]

    def video_session(query: str) -> TrendingVideoSession | None:
        if not video_players:
            return None
        return ManagedTrendingVideoSession(video_players[0], query)

    def bind_song_launch(handler: Callable[[SongLaunchRequest], None]) -> None:
        song_launch[:] = [handler]

    def trending_panel_factory(
        parent: tk.Misc, theme: ThemeBundle, on_back: Callable[[], None]
    ) -> TrendingRadioPanel:
        generation = [0]
        panel: TrendingRadioPanel

        def refresh(station: str, period: str, kind: str = "songs") -> None:
            generation[0] += 1
            request = generation[0]
            if not network_allowed():
                panel.set_error("Offline mode")
                return

            def work() -> None:
                try:
                    stations = charts.stations()
                    chart = (charts.artists if kind == "artists" else charts.songs)(
                        station=None if station == "All stations" else station,
                        period=period,
                        limit=40,
                    )
                    error = None
                except Exception as exc:
                    stations, chart, error = [], {}, str(exc)

                def deliver() -> None:
                    if closed() or request != generation[0] or not panel.winfo_exists():
                        return
                    if error is not None:
                        panel.set_error("Check the service and refresh.")
                        notification_sink.publish(
                            Notification(
                                code="musicforge.charts_unavailable",
                                title="MusicForge Charts Unavailable",
                                message=error or "The Airplay API did not return charts.",
                                severity=NotificationSeverity.ERROR,
                                source="musicforge",
                            )
                        )
                    else:
                        panel.set_stations(stations)
                        panel.set_chart(chart, kind=kind)

                dispatch_ui(deliver)

            run_work(work)

        def play(request: SongLaunchRequest) -> None:
            if not song_launch:
                media_error("YouTube", "YouTube search is not configured.")
                return
            song_launch[0](request)

        def load_artist(artist: str) -> None:
            def work() -> None:
                if closed() or not network_allowed():
                    return
                try:
                    profile = profiles.get(artist)
                except (OSError, ValueError, KeyError, IndexError, TypeError):
                    return

                def deliver() -> None:
                    if not closed() and panel.winfo_exists() and network_allowed():
                        panel.set_artist_profile(artist, profile)

                dispatch_ui(deliver)

            run_work(work)

        def media_error(provider: str, message: str) -> None:
            notification_sink.publish(
                Notification(
                    code=f"trending.{provider.lower()}_unavailable",
                    title=f"{provider} Unavailable",
                    message=message or f"{provider} could not open.",
                    severity=NotificationSeverity.ERROR,
                    source="trending",
                )
            )

        def search_artist(destination: SongDestination, artist: str) -> None:
            if destination is SongDestination.SPOTIFY:
                provider = "Spotify"
                url = f"https://open.spotify.com/search/{quote(artist, safe='')}"
            else:
                provider = "YouTube"
                url = f"https://www.youtube.com/results?{urlencode({'search_query': artist})}"

            def open_search() -> None:
                try:
                    if closed() or not network_allowed() or webbrowser.open(url):
                        return
                    message = "Could not open the browser for artist search."
                except (OSError, webbrowser.Error) as error:
                    message = str(error)
                dispatch_ui(
                    lambda: media_error(provider, message) if panel.winfo_exists() else None
                )

            run_work(open_search)

        panel = TrendingRadioPanel(
            parent,
            theme=theme,
            on_back=on_back,
            on_refresh=refresh,
            on_play=play,
            on_media_error=media_error,
            on_artist_search=search_artist,
            on_artist_selected=load_artist,
            video_session=video_session,
            spotify_factory=lambda host, back, artist, title: (
                spotify_factories[0](host, back, artist, title) if spotify_factories else None
            ),
            online_allowed=network_allowed,
        )
        return panel

    return TrendingBindings(
        trending_panel_factory,
        bind_song_launch,
        bind_video_player,
        bind_spotify_factory,
        charts.close,
    )
