# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level composition for the complete ORC UI application."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from controllers.navigation.map_controls_drawer_controller import MapControlsDrawerController
from dataclasses import dataclass, field

from common.resource_cleanup import ResourceCleanup, close_resources
import math

from common.app_settings import AppSettings, AppSettingsStore
from apps.launchers.host_location_permission import HostLocationPermission
from controllers.navigation.host_location_settings_controller import HostLocationSettingsController
from controllers.weather.radar_palette import RadarPalette

from apps.orcUi.application_runtime import OrcUiApplicationRuntime, create_orc_ui_application_runtime
from apps.orcUi.composition.core import CoreComposition, create_core_composition
from apps.orcUi.cesium_map_runtime import CesiumMapRuntime
from apps.launchers.cesium_embedded_viewer import CesiumEmbeddedViewer
from controllers.navigation.current_position import get_current_position
from ui.navigation.cesium_viewer_state import CesiumViewerState
from ui.navigation import GeoPoint
from apps.orcUi.composition.games import configure_games
from apps.orcUi.composition.navigation_places import NavigationPlacesFactory
from apps.orcUi.composition.tooltips import TooltipFactory
from apps.orcUi.composition.media import MediaComposition, configure_media
from apps.orcUi.composition.radio import RadioComposition, configure_radio
from apps.orcUi.composition.road_speed_limit import RoadSpeedLimitComposition, configure_road_speed_limit
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
from frontends.tk.media.home_spectrum_strip import HomeSpectrumStrip
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
    host_location: HostLocationSettingsController | None = None
    startup_progress: Callable[[str, str], None] | None = None
    road_speed_limit: RoadSpeedLimitComposition | None = None

    _closed: bool = field(default=False, init=False)

    @property
    def app(self) -> OrcUiApp:
        return self.core.app

    def run(self) -> None:
        """Run Tk, close every owned resource, then honor host lifecycle intent."""
        with ResourceCleanup() as cleanup:
            cleanup.callback(self.close)
            _report(self.startup_progress, "runtime_start", "Starting background runtimes…")
            if self.performance is not None:
                self.performance.start()
            if self.performance_status is not None:
                self.performance_status.start()
            self.app.schedule_ui_callback(1500, self.runtime.start_background_apps)
            self.core.start()
            _report(self.startup_progress, "ready", "OpenRoadCode UI ready")
            self.app.run()

        self.core.lifecycle.execute_requested_action()

    def close(self) -> None:
        """Attempt all owned cleanup once, including before the UI loop starts."""
        if self._closed:
            return
        self._closed = True
        close_resources(
            self.app.shutdown,
            *(resource.close for resource in (
                self.road_speed_limit, self.host_location, self.performance_status,
                self.performance, self.vision, self.navigation,
                self.navigation_places, self.radar_replay, self.weather_overlays,
            ) if resource is not None),
            self.radio.close,
            self.games.shutdown,
            self.media.close,
            self.weather.close,
            self.core.close,
            self.runtime.close,
        )


def _report(
    progress: Callable[[str, str], None] | None,
    stage: str,
    message: str,
) -> None:
    if progress is not None:
        progress(stage, message)


def create_orc_ui_composition(
    *,
    progress: Callable[[str, str], None] | None = None,
) -> OrcUiComposition:
    """Create all shell, runtime, and feature dependencies in one place."""
    with ResourceCleanup() as cleanup:
        runtime = create_orc_ui_application_runtime()
        cleanup.callback(runtime.close)
        _report(progress, "application_runtime", "Application runtime loaded")
        core = create_core_composition()
        cleanup.callback(core.close)
        _report(progress, "core", "Core UI and telemetry loaded")
        app = core.app
        app.set_theme_change_handler(core.map_runtime.set_theme)
        core.map_runtime.set_theme(app.theme_mode)
        core.presentation.observe_weather_alert(app.present_weather_alert)
        for destination in ("HOME", "NAVIGATION", "RADIO", "VEHICLE", "VISION", "MEDIA", "GAMES", "LIGHTING"):
            app.register_navigation_destination(destination)
        radio = configure_radio(app, runtime)
        cleanup.callback(radio.close)
        _report(progress, "radio", "Radio subsystem loaded")
        games = configure_games(app)
        cleanup.callback(games.shutdown)
        _report(progress, "games", "Games subsystem loaded")
        vision = configure_vision(app)
        cleanup.callback(vision.close)
        _report(progress, "vision", "Vision subsystem loaded")
        media = configure_media(app, runtime)
        cleanup.callback(media.close)
        _report(progress, "media", "Media subsystem loaded")
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
        cleanup.callback(weather.close)
        _report(progress, "weather", "Weather subsystem loaded")
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
        road_speed_limit = configure_road_speed_limit(app, core.presentation, home)
        cleanup.callback(road_speed_limit.close)
        weather_view = NavigationRouteWeather(app, lambda: theme_bundle(app.theme_mode), unit_system)
        overlays = configure_weather_overlays(app, weather_view, core.map_camera.renderer_client,
                                             weather.radar_tiles, unit_system, core.route_request_handler,
                                             core.presentation)
        cleanup.callback(overlays.close)
        navigation_maps = CesiumMapRuntime(core.map_runtime, CesiumEmbeddedViewer(),
            initial_view=lambda: CesiumViewerState(get_current_position() or
                GeoPoint(math.radians(42.3314),math.radians(-83.0458)), label="Terrain", destination_marker_visible=False))
        cleanup.callback(navigation_maps.close)
        core.map_camera.observe_position(navigation_maps.update_position)
        navigation_places = NavigationPlacesFactory(
            online_allowed=lambda: app.online_mode.online,
            camera_observer=core.map_camera.request_handler.observe_camera,
            embedded_explore=navigation_maps.request_explore)
        cleanup.callback(navigation_places.close)
        navigation = NavigationScreen(
            app,
            drawer_handler=MapControlsDrawerController(),
            online_mode=app.online_mode,
            map_runtime=navigation_maps,
            map_platform=navigation_maps,
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
        cleanup.callback(navigation.close)
        radar_replay = RadarReplayController(app, navigation, weather.radar, injection=weather.radar_injection,
                                              on_palette=set_radar_palette, on_visibility=home.refresh_radar_state,
                                              on_source=weather.select_radar_source,
                                              refresh_renderer=refresh_radar_map_state)
        cleanup.callback(radar_replay.close)
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
        permission = HostLocationPermission()
        host_location = HostLocationSettingsController(app, settings, permission, available=permission.available)
        cleanup.callback(host_location.close)
        settings.set_host_location_request_handler(host_location)
        performance = SystemPerformanceMonitor()
        cleanup.callback(performance.close)
        diagnostics = DiagnosticsScreen(
            app, provider=performance, history=performance.history,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            on_back=app.close_diagnostics,
        )
        performance_status = PerformanceStatusPresenter(app, performance, app.set_performance_status)
        cleanup.callback(performance_status.close)
        home.set_radio_factory(radio.home_factory)
        home.set_media_factory(media.home_factory)
        if media.home_spectrum is not None:
            def home_spectrum_factory(parent: tk.Misc) -> tk.Widget:
                return HomeSpectrumStrip(parent, feed=media.home_spectrum,
                    background=theme_bundle(app.theme_mode).ui.surface,
                    on_open=media.visualizer.show)
            home.set_spectrum_factory(home_spectrum_factory)
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
        _report(progress, "screens", "Application screens loaded")
        composition = OrcUiComposition(
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
            host_location=host_location,
            startup_progress=progress,
            road_speed_limit=road_speed_limit,
        )
        cleanup.release()
        return composition
