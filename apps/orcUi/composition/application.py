# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level composition for the complete ORC UI application."""

from __future__ import annotations

import os
from collections.abc import Callable

from adapters.radio.json_radio_visualization_settings import JsonRadioVisualizationSettings
from adapters.radio.sdrforge_rf_hardware_config import SdrForgeRfHardwareConfig
from apps.launchers.host_location_permission import HostLocationPermission
from apps.launchers.host_location_session import HostLocationSession
from apps.launchers.scrcpy_waze_launcher import ScrcpyWazeLauncher
from apps.launchers.waydroid_location_provider import WaydroidLocationProvider
from apps.orcUi.adapters.scrcpy_waze_gestures import ScrcpyWazeGestures
from apps.orcUi.adapters.scrcpy_waze_player import ScrcpyWazePlayer
from apps.orcUi.application_runtime import create_orc_ui_application_runtime
from apps.orcUi.composition.android_app_view import AndroidAppView
from apps.orcUi.composition.application_resources import (
    OrcUiComposition,
    _report,
    bind_settings_navigation,
    create_audio_settings,
    create_navigation_maps,
    create_software_update,
)
from apps.orcUi.composition.business_apps import (
    _android_panel_backends,
    configure_termux_business_apps,
)
from apps.orcUi.composition.calendar import (
    CalendarConfiguration,
    configure_calendar,
    create_home_calendar_factory,
)
from apps.orcUi.composition.core import create_core_composition
from apps.orcUi.composition.games import configure_games
from apps.orcUi.composition.media import configure_media
from apps.orcUi.composition.navigation_places import NavigationPlacesFactory
from apps.orcUi.composition.radio import configure_radio
from apps.orcUi.composition.tooltips import TooltipFactory
from apps.orcUi.composition.waze import configure_waze
from apps.orcUi.composition.weather import configure_weather
from apps.orcUi.composition.weather_overlays import configure_weather_overlays
from apps.orcUi.frontend.tk.home_screen import HomeScreen
from apps.orcUi.frontend.tk.navigation_route_weather import NavigationRouteWeather
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
from apps.orcUi.frontend.tk.offroad_screen import OffRoadScreen
from apps.orcUi.frontend.tk.settings_screen import SettingsScreen
from apps.orcUi.frontend.tk.vehicle_screen import VehicleScreen
from apps.orcUi.performance_status import PerformanceStatusPresenter
from apps.orcUi.theme_runtime import theme_bundle
from common.app_settings import AppSettingsStore
from common.resource_cleanup import ResourceCleanup
from controllers.navigation.host_location_settings_controller import HostLocationSettingsController
from controllers.navigation.location_sharing_controller import LocationSharingController
from controllers.navigation.map_controls_drawer_controller import MapControlsDrawerController
from controllers.navigation.map_favorites import MapFavorites
from controllers.navigation.navigation_experience_controller import NavigationExperienceController
from controllers.navigation.navigation_view_controller import NavigationViewController
from controllers.navigation.waze_gesture_controller import WazeGestureController
from controllers.weather.radar_palette import RadarPalette
from controllers.weather.radar_replay_controller import RadarReplayController
from frontends.tk.system.diagnostics_screen import DiagnosticsScreen
from frontends.x11.x11_window_embedder import X11WindowEmbedder
from services.common.system_performance_monitor import SystemPerformanceMonitor
from ui.navigation.map_platform_if import MapPlatform
from ui.navigation.waze_request_handler_if import WazeSessionState


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
            if destination != "VISION" or os.environ.get("ORC_NO_CAMERA") != "1":
                app.register_navigation_destination(destination)
        rf_visualization_settings = JsonRadioVisualizationSettings()
        radio = configure_radio(app, runtime, rf_visualization_settings)
        cleanup.callback(radio.close)
        _report(progress, "radio", "Radio subsystem loaded")
        games = configure_games(app)
        cleanup.callback(games.shutdown)
        _report(progress, "games", "Games subsystem loaded")
        vision = None
        if os.environ.get("ORC_NO_CAMERA") == "1":
            _report(progress, "vision", "Vision subsystem intentionally disabled")
        else:
            from apps.orcUi.composition.vision import configure_vision

            vision = configure_vision(app)
            cleanup.callback(vision.close)
            _report(progress, "vision", "Vision subsystem loaded")
        media = configure_media(app, runtime)
        cleanup.callback(media.close)
        radio.bind_song_launch(media.song_launch_controller.launch_song)
        radio.bind_video_player(media.trending_youtube_player)
        radio.bind_spotify_factory(media.trending_spotify_factory)
        _report(progress, "media", "Media subsystem loaded")
        settings_store = AppSettingsStore()
        app_settings = settings_store.load()

        def unit_system():
            return app_settings.unit_system

        def set_unit_system(value):
            nonlocal app_settings
            app_settings = settings_store.update(unit_system=value)

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
            app_settings = settings_store.update(radar_palette=value.value)

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
        weather_view = NavigationRouteWeather(
            app, lambda: theme_bundle(app.theme_mode), unit_system
        )
        overlays = configure_weather_overlays(
            app,
            weather_view,
            core.map_camera.renderer_client,
            weather.radar_tiles,
            unit_system,
            core.route_request_handler,
            core.presentation,
        )
        cleanup.callback(overlays.close)
        navigation_maps, navigation_map_requests = create_navigation_maps(core, cleanup)
        host_location = None
        waydroid_enabled, scrcpy_enabled = _android_panel_backends()

        def location_status(location, android):
            if host_location is not None:
                host_location.update_location_status(location, android)

        def host_sharing_changed(sharing):
            if host_location is not None:
                host_location.update_host_sharing(sharing)

        location_sharing = LocationSharingController(
            WaydroidLocationProvider.from_config() if waydroid_enabled else None,
            status=location_status,
            android_requested=waydroid_enabled,
            sharing_changed=host_sharing_changed,
        )
        cleanup.callback(location_sharing.close)
        core.map_camera.observe_location(location_sharing.update_snapshot)
        android_app_view = None
        installed_business_apps = None
        waze_app_view = None
        waze_native_launcher = None
        waze_gestures = None
        if scrcpy_enabled and not waydroid_enabled:
            scrcpy_player = ScrcpyWazePlayer(retain_session=True)
            scrcpy_embedder = X11WindowEmbedder()
            waze_gestures = WazeGestureController(
                ScrcpyWazeGestures(scrcpy_player, scrcpy_embedder)
            )
            cleanup.callback(waze_gestures.close)
        waze = None
        navigation_view = NavigationViewController(
            open_map=lambda: app.navigate_to("NAVIGATION"),
            open_waze=lambda: (
                waze.request_open_waze() if waze is not None else app.navigate_to("NAVIGATION")
            ),
        )
        app.register_navigation_action("NAVIGATION", navigation_view.request_resume_navigation)
        close_waze = lambda: waze.request_close_waze() if waze is not None else None
        saved_waze_destination = lambda key: (
            waze.request_navigate_saved_destination(key) if waze is not None else None
        )
        # Late-bound view callbacks keep platform/app logic outside Tk widgets.
        experiences = NavigationExperienceController(
            platform=navigation_maps,
            navigation_state=lambda: navigation_view.state,
            open_map=lambda: app.navigate_to("NAVIGATION"),
            open_waze=lambda: waze.request_open_waze() if waze is not None else None,
            waze_state=lambda: (
                waze.native.state
                if waze is not None and waze.native is not None
                else WazeSessionState()
            ),
            waze_available=lambda: waze is not None and waze.native is not None,
            saved_map=lambda key: navigation.request_saved_destination(key),
            saved_waze=saved_waze_destination,
            show_places=lambda: navigation.request_places_drawer(),
            search_places=lambda category, transit: navigation.request_search_places(
                category, transit
            ),
            select_place=lambda place: navigation.request_select_place(place),
            clear_places=lambda: navigation.request_clear_places(),
            close_waze=close_waze,
            select_platform=lambda platform: navigation.request_map_platform(platform),
            gestures=waze_gestures,
        )
        if waydroid_enabled:
            android_app_view = AndroidAppView(
                app,
                map_runtime=navigation_maps,
                map_platform=navigation_maps,
                map_presentation=core.map_camera,
                visibility_changed=location_sharing.set_active,
            )
            cleanup.callback(android_app_view.close)
            waze_app_view = AndroidAppView(
                app,
                map_runtime=navigation_maps,
                map_platform=navigation_maps,
                map_presentation=core.map_camera,
                screen_label="WAZE_NATIVE",
                navigation_label="NAVIGATION",
                persistent_session=True,
                close_action=close_waze,
                saved_destination_action=saved_waze_destination,
                on_present=navigation_view.remember_waze,
                experience_handler=experiences,
            )
            cleanup.callback(waze_app_view.close)
        elif scrcpy_enabled:
            android_app_view, installed_business_apps = configure_termux_business_apps(
                app,
                map_runtime=navigation_maps,
                map_platform=navigation_maps,
                map_presentation=core.map_camera,
            )
            if android_app_view is not None:
                cleanup.callback(android_app_view.close)
            waze_app_view = AndroidAppView(
                app,
                map_runtime=navigation_maps,
                map_platform=navigation_maps,
                map_presentation=core.map_camera,
                player=scrcpy_player,
                window_embedder=scrcpy_embedder,
                preserve_external_window=False,
                screen_label="WAZE_NATIVE",
                navigation_label="NAVIGATION",
                persistent_session=True,
                close_action=close_waze,
                saved_destination_action=saved_waze_destination,
                on_present=navigation_view.remember_waze,
                experience_handler=experiences,
                visibility_changed=waze_gestures.set_visible,
            )
            cleanup.callback(waze_app_view.close)
            waze_native_launcher = ScrcpyWazeLauncher(
                prepare_destination=scrcpy_player.prepare_destination,
                stop_viewer=scrcpy_player.stop,
            )
        saved_destinations = MapFavorites()
        navigation_places = NavigationPlacesFactory(
            favorites=saved_destinations,
            online_allowed=lambda: app.online_mode.online,
            camera_observer=core.map_camera.request_handler.observe_camera,
            embedded_explore=navigation_maps.request_explore,
            android_app_view=android_app_view,
            installed_apps=installed_business_apps,
            viewport_search_enabled=lambda: navigation_maps.state.active is MapPlatform.MAPLIBRE,
            marker_selection_source=navigation_maps,
        )
        cleanup.callback(navigation_places.close)
        waze = configure_waze(
            app,
            runtime,
            android_app_view=waze_app_view,
            native_launcher=waze_native_launcher,
            session_changed=lambda state: location_sharing.set_navigation_active(state.active),
            saved_destination=saved_destinations.shortcut_position,
        )
        if waze is not None:
            cleanup.callback(waze.close)
        navigation = NavigationScreen(
            app,
            drawer_handler=MapControlsDrawerController(),
            online_mode=app.online_mode,
            map_runtime=navigation_maps,
            map_platform=navigation_maps,
            waze_handler=waze,
            experience_handler=experiences,
            on_show=navigation_view.remember_map,
            places_factory=navigation_places,
            tooltip_factory=TooltipFactory(app),
            map_request_handler=navigation_map_requests,
            route_request_handler=core.route_request_handler,
            route_simulation_handler=core.route_request_handler,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            telemetry_profile_request=core.telemetry_profile_request,
            on_back=lambda: app.navigate_to("HOME"),
            route_weather=weather_view,
        )
        cleanup.callback(navigation.close)
        radar_replay = RadarReplayController(
            app,
            navigation,
            weather.radar,
            injection=weather.radar_injection,
            on_palette=set_radar_palette,
            on_visibility=home.refresh_radar_state,
            on_source=weather.select_radar_source,
            refresh_renderer=refresh_radar_map_state,
        )
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
        audio_settings = create_audio_settings(app)
        if audio_settings is not None:
            cleanup.callback(audio_settings.close)
        settings = SettingsScreen(
            app,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            telemetry_profile_request=core.telemetry_profile_request,
            vehicle_configuration=lambda: core.vehicle_configuration.configuration,
            on_vehicle_configuration_changed=core.vehicle_configuration.update,
            unit_system=unit_system,
            on_unit_system_changed=set_unit_system,
            on_back=lambda: app.navigate_to("HOME"),
            rf_hardware_config=SdrForgeRfHardwareConfig(app),
            rf_visualization_settings=rf_visualization_settings,
            receiver_settings=radio.receiver_settings,
            audio_settings=audio_settings,
            performance_overlay_enabled=app.performance_overlay_enabled,
            on_performance_overlay_changed=app.set_performance_overlay_enabled,
            configure_spotify=media.configure_spotify,
            close_spotify_configuration=media.close_spotify_configuration,
        )
        host_location_session = HostLocationSession()
        cleanup.callback(host_location_session.close)
        permission = HostLocationPermission(recover=host_location_session.start)
        cleanup.callback(permission.close)
        host_location = HostLocationSettingsController(
            app, settings, permission, available=permission.available
        )
        cleanup.callback(host_location.close)
        settings.set_host_location_request_handler(host_location)
        host_location.restore_if_running()
        location_sharing.start()
        performance = SystemPerformanceMonitor()
        cleanup.callback(performance.close)
        diagnostics = DiagnosticsScreen(
            app,
            provider=performance,
            history=performance.history,
            theme_bundle=lambda: theme_bundle(app.theme_mode),
            on_back=app.close_diagnostics,
            sdrforge_diagnostics=(
                radio.rigctl_client.connection_diagnostics
                if radio.rigctl_client is not None
                else None
            ),
        )
        performance_status = PerformanceStatusPresenter(
            app, performance, app.set_performance_status, on_sample=app.update_performance_overlay
        )
        cleanup.callback(performance_status.close)
        home.set_radio_factory(radio.home_factory)
        home.set_media_factory(media.home_factory)
        home.set_visualizer_factory(media.home_visualizer_factory)
        core.presentation.observe_vehicle(home.apply_vehicle_state)
        core.presentation.observe_trip(home.apply_trip_state)
        core.presentation.observe_position(home.apply_position_state)
        core.presentation.observe_position(app.set_position_state)
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
        calendar_config = CalendarConfiguration()
        configure_calendar(app, calendar_config)
        calendar_factory = create_home_calendar_factory(
            app, calendar_config, core.route_request_handler
        )
        home.set_calendar_factory(calendar_factory, calendar_factory.monitor)
        app.set_initial_destination("HOME")
        bind_settings_navigation(app, settings, audio_settings)
        _report(progress, "screens", "Application screens loaded")
        software_update = create_software_update(core, app)
        cleanup.callback(software_update.close)
        composition = OrcUiComposition(
            core=core,
            runtime=runtime,
            radio=radio,
            media=media,
            games=games,
            weather=weather,
            vision=vision,
            home=home,
            appointment_monitor=calendar_factory.monitor,
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
            host_location_session=host_location_session,
            host_location_permission=permission,
            location_sharing=location_sharing,
            startup_progress=progress,
            waze=waze,
            android_app_view=android_app_view,
            waze_app_view=waze_app_view,
            waze_gestures=waze_gestures,
            software_update=software_update,
            audio_settings=audio_settings,
        )
        cleanup.release()
        return composition
