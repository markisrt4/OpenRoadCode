# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level composition for the complete ORC UI application."""

from __future__ import annotations

from dataclasses import dataclass

from common.app_settings import AppSettings, AppSettingsStore
from controllers.weather.radar_palette import RadarPalette

from apps.orcUi.application_runtime import OrcUiApplicationRuntime, create_orc_ui_application_runtime
from apps.orcUi.composition.core import CoreComposition, create_core_composition
from apps.orcUi.navigation_map_runtime import NavigationMapRuntime
from apps.orcUi.composition.games import configure_games
from apps.orcUi.composition.navigation_places import NavigationPlacesFactory
from apps.orcUi.composition.tooltips import TooltipFactory
from apps.orcUi.composition.media import MediaComposition, configure_media
from apps.orcUi.composition.radio import RadioComposition, configure_radio
from apps.orcUi.composition.weather import WeatherComposition, configure_weather
from apps.orcUi.composition.weather_overlays import configure_weather_overlays
from apps.orcUi.composition.vision import VisionComposition, configure_vision
from controllers.weather.weather_overlay_controller import WeatherOverlayController
from controllers.weather.radar_replay_controller import RadarReplayController
from apps.orcUi.frontend.tk.home_screen import HomeScreen
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
from apps.orcUi.frontend.tk.navigation_route_weather import NavigationRouteWeather
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.offroad_screen import OffRoadScreen
from apps.orcUi.frontend.tk.settings_screen import SettingsScreen
from apps.orcUi.frontend.tk.vehicle_screen import VehicleScreen
from apps.orcUi.performance_status import PerformanceStatusPresenter
from apps.orcUi.theme_runtime import theme_bundle
from frontends.tk.games import GamesScreen
from frontends.tk.system.diagnostics_screen import DiagnosticsScreen
from services.common.system_performance_monitor import SystemPerformanceMonitor


@dataclass(slots=True)
class OrcUiComposition:
    """Own every top-level object created for one ORC UI process."""

    core: CoreComposition
    runtime: OrcUiApplicationRuntime
    radio: RadioComposition
    media: MediaComposition
    games: GamesScreen
    weather: WeatherComposition
    vision: VisionComposition | None = None
    home: HomeScreen | None = None
    navigation: NavigationScreen | None = None
    vehicle: VehicleScreen | None = None
    offroad: OffRoadScreen | None = None
    settings: SettingsScreen | None = None
    weather_overlays: WeatherOverlayController | None = None
    radar_replay: RadarReplayController | None = None
    navigation_places: NavigationPlacesFactory | None = None
    performance: SystemPerformanceMonitor | None = None
    diagnostics: DiagnosticsScreen | None = None
    performance_status: PerformanceStatusPresenter | None = None

    @property
    def app(self) -> OrcUiApp:
        return self.core.app

    def run(self) -> None:
        """Run Tk, close every owned resource, then honor host lifecycle intent."""
        try:
            if self.performance is not None:
                self.performance.start()
            if self.performance_status is not None:
                self.performance_status.start()
            self.app.schedule_ui_callback(1500, self.runtime.start_background_apps)
            self.core.start()
            self.app.run()
        finally:
            try:
                if self.performance_status is not None:
                    self.performance_status.close()
            finally:
                try:
                    if self.performance is not None:
                        self.performance.close()
                finally:
                    try:
                        try:
                            try:
                                if self.navigation is not None:
                                    self.navigation.close()
                            finally:
                                if self.navigation_places is not None:
                                    self.navigation_places.close()
                        finally:
                            try:
                                if self.radar_replay is not None:
                                    self.radar_replay.close()
                            finally:
                                if self.weather_overlays is not None:
                                    self.weather_overlays.close()
                    finally:
                        try:
                            if self.vision is not None:
                                self.vision.close()
                        finally:
                            try:
                                self.games.shutdown()
                            finally:
                                try:
                                    self.media.close()
                                finally:
                                    try:
                                        self.weather.close()
                                    finally:
                                        try:
                                            self.core.close()
                                        finally:
                                            self.runtime.close()

        self.core.lifecycle.execute_requested_action()


def create_orc_ui_composition() -> OrcUiComposition:
    """Create all shell, runtime, and feature dependencies in one place."""
    runtime = create_orc_ui_application_runtime()
    core: CoreComposition | None = None
    overlays: WeatherOverlayController | None = None
    radar_replay: RadarReplayController | None = None
    navigation_places: NavigationPlacesFactory | None = None
    games: GamesScreen | None = None
    vision: VisionComposition | None = None
    media: MediaComposition | None = None
    navigation_maps: NavigationMapRuntime | None = None
    try:
        core = create_core_composition()
        app = core.app
        app.set_theme_change_handler(core.map_runtime.set_theme)
        core.map_runtime.set_theme(app.theme_mode)
        core.presentation.observe_weather_alert(app.present_weather_alert)
        for destination in (
            "HOME",
            "NAVIGATION",
            "RADIO",
            "VEHICLE",
            "VISION",
            "MEDIA",
            "GAMES",
            "LIGHTING",
        ):
            app.register_navigation_destination(destination)
        radio = configure_radio(app, runtime)
        games = configure_games(app)
        vision = configure_vision(app)
        media = configure_media(app, runtime)
        settings_store = AppSettingsStore()
        app_settings = settings_store.load()

        def unit_system():
            return app_settings.unit_system

        def set_unit_system(value):
            nonlocal app_settings
            app_settings = AppSettings(
                unit_system=value, radar_palette=app_settings.radar_palette
            )
            settings_store.save(app_settings)

        def open_radar_map() -> None:
            app.navigate_to("NAVIGATION")
            navigation.set_radar_enabled(True)

        weather = configure_weather(
            app,
            unit_system=unit_system,
            radar_palette=RadarPalette(app_settings.radar_palette),
            on_weather_radio=radio.open_weather_radio,
            on_radar_map=open_radar_map,
            on_weather_status=app.set_weather_status,
            map_renderer=core.map_camera.renderer_client,
        )
        def set_radar_palette(value: RadarPalette) -> None:
            nonlocal app_settings
            app_settings = AppSettings(
                unit_system=app_settings.unit_system,
                radar_palette=value.value,
            )
            settings_store.save(app_settings)

        def navigate_home_context(name: str) -> None:
            context_name = name.strip().upper()
            if not context_name:
                raise ValueError("Context destination must not be empty")
            if context_name == "TRIP":
                app.navigate_to("VEHICLE")
                vehicle.show_trip_view()
            else:
                app.navigate_to(context_name)

        def refresh_radar_map_state() -> None:
            core.map_camera.refresh_renderer_position()
            weather.radar.refresh_renderer_state()

        home = HomeScreen(
            app,
            map_runtime=core.map_runtime,
            map_request_handler=core.map_camera.request_handler,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            presentation=core.presentation,
            telemetry_profile_request=core.telemetry_profile_request,
            on_expand_context=navigate_home_context,
            radar_enabled=lambda: navigation.radar_enabled,
            on_radar_toggle=lambda enabled: navigation.set_radar_enabled(enabled),
            refresh_radar=refresh_radar_map_state,
        )
        weather_view = NavigationRouteWeather(app, lambda: theme_bundle(app.theme_mode), unit_system)
        overlays = configure_weather_overlays(app, weather_view, core.map_camera.renderer_client,
                                             weather.radar_tiles, unit_system, core.route_request_handler,
                                             core.presentation)
        navigation_places = NavigationPlacesFactory(
            online_allowed=lambda: app.online_mode.online,
            camera_observer=core.map_camera.request_handler.observe_camera)
        navigation = NavigationScreen(
            app,
            online_mode=app.online_mode,
            map_runtime=core.map_runtime,
            places_factory=navigation_places,
            tooltip_factory=TooltipFactory(app),
            map_request_handler=core.map_camera.request_handler,
            route_request_handler=core.route_request_handler,
            route_simulation_handler=core.route_request_handler,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            telemetry_profile_request=core.telemetry_profile_request,
            on_back=lambda: app.navigate_to("HOME"),
            route_weather=weather_view,
        )
        radar_replay = RadarReplayController(app, navigation, weather.radar, injection=weather.radar_injection,
                                              on_palette=set_radar_palette, on_visibility=home.refresh_radar_state,
                                              on_source=weather.select_radar_source,
                                              refresh_renderer=refresh_radar_map_state)
        navigation.set_radar_request_handler(radar_replay)
        vehicle = VehicleScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            presentation=core.presentation,
            telemetry_profile_request=core.telemetry_profile_request,
            vehicle_configuration=lambda: core.vehicle_configuration.configuration,
            on_back=lambda: app.navigate_to("HOME"),
        )
        offroad = OffRoadScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            presentation=core.presentation,
            on_back=lambda: app.navigate_to("HOME"),
        )
        settings = SettingsScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            telemetry_profile_request=core.telemetry_profile_request,
            vehicle_configuration=lambda: core.vehicle_configuration.configuration,
            on_vehicle_configuration_changed=core.vehicle_configuration.update,
            unit_system=unit_system,
            on_unit_system_changed=set_unit_system,
            on_back=lambda: app.navigate_to("HOME"),
        )
        performance = SystemPerformanceMonitor()
        diagnostics = DiagnosticsScreen(
            app, provider=performance, history=performance.history,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            on_back=app.close_diagnostics,
        )
        performance_status = PerformanceStatusPresenter(app, performance, app.set_performance_status)
        home.set_radio_factory(radio.home_factory)
        home.set_media_factory(media.home_factory)
        core.presentation.observe_vehicle(home.apply_vehicle_state)
        core.presentation.observe_trip(home.apply_trip_state)
        core.presentation.observe_position(home.apply_position_state)
        core.presentation.observe_attitude(home.apply_attitude_state)
        core.presentation.observe_vehicle(vehicle.apply_vehicle_state)
        core.presentation.observe_trip(vehicle.apply_trip_state)
        core.presentation.observe_engine_analysis(vehicle.apply_engine_analysis)
        core.presentation.observe_position(vehicle.apply_position_state)
        core.presentation.observe_attitude(vehicle.apply_attitude_state)
        core.presentation.observe_position(offroad.apply_position_state)
        core.presentation.observe_attitude(offroad.apply_attitude_state)
        core.vehicle_configuration.observe(vehicle.set_vehicle_configuration)
        app.register_screen("HOME", home)
        app.register_screen("NAVIGATION", navigation)
        app.register_screen("VEHICLE", vehicle)
        app.register_screen("OFF-ROAD", offroad, show_in_navigation=False)
        app.register_screen("SETTINGS", settings, show_in_navigation=False)
        app.register_screen("DIAGNOSTICS", diagnostics, show_in_navigation=False)
        app.set_initial_destination("HOME")
        app.set_settings_action(lambda: app.navigate_to("SETTINGS"))
    except Exception:
        try:
            try:
                if navigation_maps is not None:
                    navigation_maps.close()
            finally:
                try:
                    if navigation_places is not None:
                        navigation_places.close()
                finally:
                    if radar_replay is not None:
                        radar_replay.close()
        finally:
            try:
                if overlays is not None:
                    overlays.close()
            finally:
                try:
                    if vision is not None:
                        vision.close()
                    if games is not None:
                        games.shutdown()
                    if media is not None:
                        media.close()
                    if core is not None:
                        core.close()
                finally:
                    runtime.close()
        raise
    return OrcUiComposition(
        core=core,
        runtime=runtime,
        radio=radio,
        media=media,
        games=games,
        weather=weather,
        vision=vision,
        home=home,
        navigation=navigation,
        vehicle=vehicle,
        offroad=offroad,
        settings=settings,
        weather_overlays=overlays,
        radar_replay=radar_replay,
        navigation_places=navigation_places,
        performance=performance,
        diagnostics=diagnostics,
        performance_status=performance_status,
    )
