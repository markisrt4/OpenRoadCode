# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own top-level ORC runtime startup, lifecycle, and resource cleanup."""

from __future__ import annotations

import math
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from apps.launchers.cesium_embedded_viewer import CesiumEmbeddedViewer
from apps.launchers.host_location_permission import HostLocationPermission
from apps.launchers.host_location_session import HostLocationSession
from apps.orcUi.application_runtime import OrcUiApplicationRuntime
from apps.orcUi.cesium_map_runtime import CesiumMapRuntime
from apps.orcUi.composition.android_app_view import AndroidAppView
from apps.orcUi.composition.core import CoreComposition
from apps.orcUi.composition.media import MediaComposition
from apps.orcUi.composition.navigation_places import NavigationPlacesFactory
from apps.orcUi.composition.radio import RadioComposition
from apps.orcUi.composition.waze import WazeComposition
from apps.orcUi.composition.weather import WeatherComposition
from apps.orcUi.frontend.tk.home_screen import HomeScreen
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
from apps.orcUi.frontend.tk.offroad_screen import OffRoadScreen
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.settings_screen import SettingsScreen
from apps.orcUi.frontend.tk.vehicle_screen import VehicleScreen
from apps.orcUi.map_platform_requests import MapPlatformRequests
from apps.orcUi.performance_status import PerformanceStatusPresenter
from common.resource_cleanup import ResourceCleanup, close_resources
from controllers.audio.linux_audio_settings import LinuxAudioSettings
from controllers.navigation.current_position import get_current_position
from controllers.navigation.host_location_settings_controller import HostLocationSettingsController
from controllers.navigation.location_sharing_controller import LocationSharingController
from controllers.navigation.route_overlay_controller import RouteOverlayController
from controllers.navigation.waze_gesture_controller import WazeGestureController
from controllers.system.software_update import CheckoutUpdates, SoftwareUpdateController
from controllers.weather.radar_replay_controller import RadarReplayController
from controllers.weather.weather_overlay_controller import WeatherOverlayController
from frontends.tk.games import GamesScreen
from frontends.tk.system.diagnostics_screen import DiagnosticsScreen
from services.common.system_performance_monitor import SystemPerformanceMonitor
from ui.calendar.calendar_presentation_if import AppointmentMonitorIf
from ui.navigation import GeoPoint
from ui.navigation.cesium_viewer_state import CesiumViewerState

if TYPE_CHECKING:
    from apps.orcUi.composition.vision import VisionComposition


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
    appointment_monitor: AppointmentMonitorIf | None = None
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
    host_location_session: HostLocationSession | None = None
    host_location_permission: HostLocationPermission | None = None
    location_sharing: LocationSharingController | None = None
    startup_progress: Callable[[str, str], None] | None = None
    software_update: SoftwareUpdateController | None = None
    audio_settings: LinuxAudioSettings | None = None
    waze: WazeComposition | None = None
    android_app_view: AndroidAppView | None = None
    waze_app_view: AndroidAppView | None = None
    waze_gestures: WazeGestureController | None = None

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
            if self.software_update is not None:
                self.software_update.start()
            self._poll_route_start()
            _report(self.startup_progress, "ready", "OpenRoadCode UI ready")
            self.app.run()

        self.core.lifecycle.execute_requested_action()

    def _poll_route_start(self) -> None:
        if self._closed:
            return
        try:
            if self.core.route_request_handler.poll_route_start():
                self.app.set_screen_status("Appointment guidance started")
                self.app.navigate_to("NAVIGATION")
        except Exception:
            self.app.set_screen_status("Unable to start appointment guidance")
        finally:
            if not self._closed:
                self.app.schedule_ui_callback(100, self._poll_route_start)

    def close(self) -> None:
        """Attempt all owned cleanup once, including before the UI loop starts."""
        if self._closed:
            return
        self._closed = True
        close_resources(
            *([self.software_update.close] if self.software_update is not None else []),
            self.app.shutdown,
            *(
                resource.close
                for resource in (
                    self.audio_settings,
                    self.appointment_monitor,
                    self.waze_gestures,
                    self.android_app_view,
                    self.waze_app_view,
                    self.waze,
                    self.host_location,
                    self.host_location_permission,
                    self.location_sharing,
                    self.host_location_session,
                    self.performance_status,
                    self.performance,
                    self.vision,
                    self.navigation,
                    self.navigation_places,
                    self.radar_replay,
                    self.weather_overlays,
                )
                if resource is not None
            ),
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


def initial_terrain_view() -> CesiumViewerState:
    """Use the current position, retaining the existing Detroit fallback."""
    return CesiumViewerState(
        get_current_position() or GeoPoint(math.radians(42.3314), math.radians(-83.0458)),
        label="3D map",
        destination_marker_visible=False,
    )


def create_audio_settings(app: OrcUiApp) -> LinuxAudioSettings | None:
    """Keep Linux audio configuration out of Android/Termux sessions."""
    if os.environ.get("ORC_NO_AUDIO") == "1":
        return None
    if sys.platform == "linux" and not (
        os.environ.get("TERMUX_VERSION") or "/com.termux/" in os.environ.get("PREFIX", "")
    ):
        return LinuxAudioSettings(app)
    return None


def create_software_update(core: CoreComposition, app: OrcUiApp) -> SoftwareUpdateController:
    """Bind updates to the current online mode and lifecycle restart request."""
    online_mode = app.online_mode

    def restart_after_update() -> None:
        core.lifecycle.request_restart_ui()
        app.shutdown()

    return SoftwareUpdateController(
        CheckoutUpdates(Path(__file__).resolve().parents[3]),
        app,
        online=lambda: online_mode is not None and online_mode.online,
        offer=app.offer_software_update,
        report_error=lambda message: app.show_error("ORC update failed", message),
        restart=restart_after_update,
    )


def create_navigation_maps(
    core: CoreComposition, cleanup: ResourceCleanup
) -> tuple[CesiumMapRuntime, MapPlatformRequests]:
    """Own the map runtime and bind the retained position, route, and POI overlays."""
    navigation_maps = CesiumMapRuntime(
        core.map_runtime,
        CesiumEmbeddedViewer(),
        initial_view=initial_terrain_view,
    )
    cleanup.callback(navigation_maps.close)
    navigation_map_requests = MapPlatformRequests(
        core.map_camera.request_handler,
        lambda _name, _args, _kwargs: None,
        navigation_maps.update_poi_overlay,
    )
    core.map_camera.observe_position(navigation_maps.update_position)
    route_overlay = RouteOverlayController(navigation_maps.update_route_overlay)
    core.route_request_handler.observe_route(route_overlay.update_route)
    core.presentation.observe_route_guidance(route_overlay.update_guidance)
    if core.route_request_handler.active_route is not None:
        route_overlay.update_route(core.route_request_handler.active_route)
    if core.presentation.route_guidance is not None:
        route_overlay.update_guidance(core.presentation.route_guidance)
    return navigation_maps, navigation_map_requests
