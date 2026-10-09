# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the ORC shell with map, volume, and state-ingress infrastructure."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from common.resource_cleanup import ResourceCleanup, close_resources

from apps.orcUi.core_runtime import MapRuntime, StateIngressRuntime
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.presentation_state import OrcUiPresentationState
from apps.orcUi.vehicle_configuration_state import VehicleConfigurationState
from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.connectivity.online_mode import OnlineModeController
from controllers.connectivity.shell_connectivity_controller import ShellConnectivityController
from controllers.audio import PipewireAudioController, SystemVolumeHandler
from controllers.automotive import AutomotiveTelemetryProfile, TripTracker
from controllers.automotive.vehicle_settings_store import VehicleSettingsStore
from controllers.automotive.fuel_model import FuelModel
from controllers.map_renderer.map_camera_runtime import MapCameraRuntime
from controllers.navigation.navigation_route_request_handler import (
    NavigationRouteRequestHandler,
)
from controllers.system import SystemLifecycleController
from messaging.contracts.automotive import AutomotiveTelemetryProfileRequestPublisher
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT, LOCAL_SUBSCRIBER_ENDPOINT
from services.automotive.automotive_service_cli import DEFAULT_RUNTIME_CONFIG
from services.navigation.navigation_command_client import NavigationCommandClient
from services.trip import TripRuntime
from ui.theme import ThemeMode


@dataclass(slots=True)
class CoreComposition:
    """Own the shell-facing infrastructure for one ORC UI process."""

    app: OrcUiApp
    presentation: OrcUiPresentationState
    vehicle_configuration: VehicleConfigurationState
    map_runtime: MapRuntime
    map_camera: MapCameraRuntime
    route_request_handler: NavigationRouteRequestHandler
    telemetry_profile_request: Callable[[AutomotiveTelemetryProfile], None]
    state_ingress: StateIngressRuntime
    trip_runtime: TripRuntime
    trip_publisher: ZeroMqPublisher
    telemetry_profile_publisher: ZeroMqPublisher
    lifecycle: SystemLifecycleController
    volume: SystemVolumeHandler
    connectivity: ShellConnectivityController | None = None

    _closed: bool = field(default=False, init=False)

    def start(self) -> None:
        if self.connectivity is not None:
            self.connectivity.start()
        self.volume.refresh()
        self.map_camera.start()
        self.state_ingress.start()
        self.trip_runtime.start()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        close_resources(
            self.app.shutdown,
            *([self.connectivity.close] if self.connectivity is not None else []),
            self.trip_runtime.close,
            self.state_ingress.close,
            self.trip_publisher.close,
            self.telemetry_profile_publisher.close,
            self.route_request_handler.close,
            self.map_camera.close,
            self.map_runtime.stop,
        )


def create_core_composition() -> CoreComposition:
    """Create the selected frontend shell and inject runtime-facing dependencies."""
    with ResourceCleanup() as cleanup:
        map_runtime = MapRuntime()
        cleanup.callback(map_runtime.stop)
        map_camera = MapCameraRuntime(
            zoom_level=16.5,
            pitch_rad=math.radians(45.0),
            follow_enabled=True,
        )
        cleanup.callback(map_camera.close)
        route_request_handler = NavigationRouteRequestHandler(NavigationCommandClient())
        cleanup.callback(route_request_handler.close)
        lifecycle = SystemLifecycleController()
        presentation = OrcUiPresentationState()
        runtime_config = ServiceRuntimeConfigParser(DEFAULT_RUNTIME_CONFIG).load()
        vehicle_settings = VehicleSettingsStore(default=runtime_config.vehicle)
        vehicle_configuration = VehicleConfigurationState(
            vehicle_settings.load(),
            save=vehicle_settings.save,
        )
        telemetry_profile_publisher = ZeroMqPublisher(LOCAL_PUBLISHER_ENDPOINT)
        cleanup.callback(telemetry_profile_publisher.close)
        telemetry_profile_requests = AutomotiveTelemetryProfileRequestPublisher(
            telemetry_profile_publisher,
            source="orc-ui",
        )
        telemetry_profile_request = telemetry_profile_requests.publish
        map_runtime.set_theme(ThemeMode.DARK)
        app = OrcUiApp(
            lifecycle_handler=lifecycle,
            online_mode=OnlineModeController(),
        )
        cleanup.callback(app.shutdown)
        connectivity = ShellConnectivityController(app.online_mode, app, app.set_online_status, app.set_screen_status)
        cleanup.callback(connectivity.close)
        app.set_connectivity_handler(connectivity.toggle)
        volume = SystemVolumeHandler(
            audio_controller=PipewireAudioController(),
            volume_ui=app,
            set_status=app.set_screen_status,
        )
        app.set_volume_request_handler(volume)
        state_ingress = StateIngressRuntime(
            schedule_ui=app.schedule_ui_callback,
            apply_vehicle_state=presentation.apply_vehicle,
            apply_engine_analysis=presentation.apply_engine_analysis,
            apply_trip_state=presentation.apply_trip,
            apply_position_state=presentation.apply_position,
            apply_attitude_state=presentation.apply_attitude,
            apply_route_guidance_state=presentation.apply_route_guidance,
            apply_weather_alert=presentation.apply_weather_alert,
            vehicle_configuration=vehicle_configuration.configuration,
        )
        cleanup.callback(state_ingress.close)
        vehicle_configuration.observe(state_ingress.set_vehicle_configuration)
        fuel_config = runtime_config.automotive.fuel
        trip_tracker = TripTracker(
            fuel_model=FuelModel(
                engine_displacement_m3=fuel_config.engine_displacement_l / 1000.0,
                volumetric_efficiency=fuel_config.volumetric_efficiency,
            )
        )
        trip_publisher = ZeroMqPublisher(LOCAL_PUBLISHER_ENDPOINT)
        cleanup.callback(trip_publisher.close)
        with ResourceCleanup() as acquired:
            trip_subscriber = ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT)
            acquired.callback(trip_subscriber.close)
            trip_runtime = TripRuntime(
                trip_subscriber,
                trip_publisher,
                tracker=trip_tracker,
                publish_source="orc-ui-trip-runtime",
            )
            cleanup.callback(trip_runtime.close)
            acquired.release()
        composition = CoreComposition(
            app=app,
            presentation=presentation,
            vehicle_configuration=vehicle_configuration,
            map_runtime=map_runtime,
            map_camera=map_camera,
            route_request_handler=route_request_handler,
            telemetry_profile_request=telemetry_profile_request,
            state_ingress=state_ingress,
            trip_runtime=trip_runtime,
            trip_publisher=trip_publisher,
            telemetry_profile_publisher=telemetry_profile_publisher,
            lifecycle=lifecycle,
            volume=volume,
            connectivity=connectivity,
        )
        cleanup.release()
        return composition
