# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own top-level ORC runtime startup, lifecycle, and resource cleanup."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from apps.launchers.host_location_permission import HostLocationPermission
from apps.launchers.host_location_session import HostLocationSession
from apps.orcUi.application_runtime import OrcUiApplicationRuntime
from apps.orcUi.composition.android_app_view import AndroidAppView
from apps.orcUi.composition.core import CoreComposition
from apps.orcUi.composition.media import MediaComposition
from apps.orcUi.composition.navigation_places import NavigationPlacesFactory
from apps.orcUi.composition.radio import RadioComposition
from apps.orcUi.composition.vision import VisionComposition
from apps.orcUi.composition.waze import WazeComposition
from apps.orcUi.composition.weather import WeatherComposition
from apps.orcUi.frontend.tk.home_screen import HomeScreen
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen
from apps.orcUi.frontend.tk.offroad_screen import OffRoadScreen
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.settings_screen import SettingsScreen
from apps.orcUi.frontend.tk.vehicle_screen import VehicleScreen
from apps.orcUi.performance_status import PerformanceStatusPresenter
from common.resource_cleanup import ResourceCleanup, close_resources
from controllers.navigation.host_location_settings_controller import HostLocationSettingsController
from controllers.navigation.location_sharing_controller import LocationSharingController
from controllers.navigation.waze_gesture_controller import WazeGestureController
from controllers.weather.radar_replay_controller import RadarReplayController
from controllers.weather.weather_overlay_controller import WeatherOverlayController
from frontends.tk.games import GamesScreen
from frontends.tk.system.diagnostics_screen import DiagnosticsScreen
from services.common.system_performance_monitor import SystemPerformanceMonitor
from ui.calendar.calendar_presentation_if import AppointmentMonitorIf


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
            self.app.shutdown,
            *(resource.close for resource in (
                self.appointment_monitor, self.waze_gestures, self.android_app_view, self.waze_app_view, self.waze, self.host_location, self.host_location_permission, self.location_sharing, self.host_location_session, self.performance_status, self.performance, self.vision, self.navigation,
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

