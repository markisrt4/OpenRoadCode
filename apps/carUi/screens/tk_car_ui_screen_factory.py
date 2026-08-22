# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk implementation of the Car UI screen-construction boundary."""

from collections.abc import Callable

from apps.carUi.car_ui_dependencies import CarUiDependencies
from apps.carUi.navigation_request_handler import NavigationRequestHandler
from apps.carUi.radio.radio_screen_binding import create_radio_screen_binding
from apps.carUi.screens.aircraft_screen import AircraftScreen
from apps.carUi.screens.car_ui_screen_factory_if import CarUiScreens
from apps.carUi.screens.fm_radio_screen import FMRadioScreen
from apps.carUi.screens.netflix_screen import NetflixScreen
from apps.carUi.screens.offroad_dashboard_screen import OffroadDashboardScreen
from apps.carUi.screens.scanner_screen import ScannerScreen
from apps.carUi.screens.weather_screen import WeatherScreen
from apps.carUi.screens.youtube_screen import YouTubeScreen
from apps.carUi.screens.vehicle_gauges_screen import VehicleGaugesScreen
from apps.common.uiTheme import LIGHTING_PANEL_THEME
from apps.common.uiTheme.uiTheme import CAR_UI_THEME
from apps.common.uiTheme.spotify import SPOTIFY_PANEL_THEME
from controllers.lighting import LightingPresenter
from controllers.audio import MediaVolumeHandler
from controllers.spotify import SpotifyMediaPresenter
from frontends.tk.lighting import LightingScreen
from frontends.tk.media import SpotifyScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf


class TkCarUiScreenFactory:
    """Create the standard Car UI destinations using Tk implementations."""

    def __init__(self, host: TkScreenHostIf, *, compact_ui: bool, create_menu_tile, show_main_menu: Callable[[], None], show_menu: Callable[[str], None]) -> None:
        self._host = host
        self._compact_ui = compact_ui
        self._create_menu_tile = create_menu_tile
        self._show_main_menu = show_main_menu
        self._show_menu = show_menu

    def create_screens(self, dependencies: CarUiDependencies, on_frequency_changed: Callable[[int], None], dispatch: Callable[[Callable[[], None]], None]) -> CarUiScreens:
        runtime = dependencies.runtime
        common = {"remote_display": runtime.remote_display, "on_frequency_changed": on_frequency_changed, "create_menu_tile": self._create_menu_tile, "binding_factory": create_radio_screen_binding}
        aircraft = AircraftScreen(self._host, airband_runtime=lambda: runtime.radios.get("airband"), adsb_launcher=runtime.adsb_launcher, auxiliary_display=runtime.auxiliary_display, home_action=self._show_main_menu, **common)
        weather = WeatherScreen(self._host, weather_radio_runtime=lambda: runtime.radios.get("weather_band"), dashboard_launcher=runtime.weather_dash_launcher, auxiliary_display=runtime.auxiliary_display, home_action=self._show_main_menu, **common)
        fm_radio = FMRadioScreen(self._host, runtime=lambda: runtime.radios.get("fm_radio"), back_action=lambda: self._show_menu("radio"), **common)
        scanner = ScannerScreen(self._host, radio_runtimes=runtime.radios, radio_menu_action=lambda: self._show_menu("radio"), compact_ui=self._compact_ui, **common)

        lighting = LightingScreen(self._host, theme=LIGHTING_PANEL_THEME, back_action=self._show_main_menu)
        lighting_presenter = LightingPresenter(backend=dependencies.lighting_controller, lighting_ui=lighting, dispatch=dispatch)
        lighting.set_lighting_request_handler(lighting_presenter)
        lighting.set_activation_callback(lighting_presenter.connect)

        spotify = SpotifyScreen(self._host, theme=SPOTIFY_PANEL_THEME, back_action=lambda: self._show_menu("media"), image_cache=dependencies.spotify_image_cache, lyrics_client=dependencies.spotify_lyrics_client, music_video_controller=dependencies.spotify_music_video_controller)
        spotify_presenter = SpotifyMediaPresenter(backend=dependencies.spotify_controller, media_ui=spotify, fallback_volume_handler=MediaVolumeHandler(dependencies.audio_controller))
        spotify.set_playback_request_handler(spotify_presenter)
        spotify.set_track_request_handler(spotify_presenter)
        spotify.set_seek_request_handler(spotify_presenter)
        spotify.set_volume_request_handler(spotify_presenter)
        spotify.set_state_loader(spotify_presenter.read_state)

        netflix = NetflixScreen(self._host, player=dependencies.netflix_player, display=dependencies.media_display or runtime.remote_display, colors=CAR_UI_THEME["colors"], back_action=lambda: self._show_menu("media"))
        youtube = YouTubeScreen(self._host, player=dependencies.youtube_player, display=dependencies.media_display or runtime.remote_display, colors=CAR_UI_THEME["colors"], back_action=lambda: self._show_menu("media"))

        offroad_dashboard = OffroadDashboardScreen(
            self._host,
            create_menu_tile=self._create_menu_tile,
            back_action=lambda: self._show_menu("gauges"),
            request_handler=NavigationRequestHandler(dependencies.navigation_controller),
        )
        vehicle_gauges = VehicleGaugesScreen(self._host, create_menu_tile=self._create_menu_tile, back_action=lambda: self._show_menu("gauges"))

        return CarUiScreens(aircraft=aircraft, weather=weather, lighting=lighting, fm_radio=fm_radio, scanner=scanner, spotify=spotify, netflix=netflix, youtube=youtube, offroad_dashboard=offroad_dashboard, vehicle_gauges=vehicle_gauges)
