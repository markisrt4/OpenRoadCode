# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the ORC shell with map, volume, and state-ingress infrastructure."""

from __future__ import annotations

import math
from dataclasses import dataclass

from apps.orcUi.core_runtime import MapRuntime, StateIngressRuntime
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.audio import PipewireAudioController, SystemVolumeHandler
from controllers.automotive import TripTracker
from controllers.automotive.vehicle_settings_store import VehicleSettingsStore
from controllers.automotive.fuel_model import FuelModel
from controllers.map_renderer.map_camera_runtime import MapCameraRuntime
from controllers.system import SystemLifecycleController
from messaging.contracts.automotive import AutomotiveTelemetryProfileRequestPublisher
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_PUBLISHER_ENDPOINT, LOCAL_SUBSCRIBER_ENDPOINT
from services.automotive.automotive_service_cli import DEFAULT_RUNTIME_CONFIG
from services.trip import TripRuntime


@dataclass(slots=True)
class CoreComposition:
    """Own the shell-facing infrastructure for one ORC UI process."""

    app: OrcUiApp
    map_runtime: MapRuntime
    map_camera: MapCameraRuntime
    state_ingress: StateIngressRuntime
    trip_runtime: TripRuntime
    trip_publisher: ZeroMqPublisher
    telemetry_profile_publisher: ZeroMqPublisher
    lifecycle: SystemLifecycleController
    volume: SystemVolumeHandler

    def start(self) -> None:
        self.volume.refresh()
        self.map_camera.start()
        self.state_ingress.start()
        self.trip_runtime.start()

    def close(self) -> None:
        try:
            self.trip_runtime.close()
        finally:
            try:
                self.state_ingress.close()
            finally:
                try:
                    self.trip_publisher.close()
                finally:
                    try:
                        self.telemetry_profile_publisher.close()
                    finally:
                        try:
                            self.map_camera.close()
                        finally:
                            self.map_runtime.stop()


def create_core_composition() -> CoreComposition:
    """Create the selected frontend shell and inject runtime-facing dependencies."""
    map_runtime = MapRuntime()
    map_camera = MapCameraRuntime(
        zoom_level=16.5,
        pitch_rad=math.radians(45.0),
        follow_enabled=True,
    )
    lifecycle = SystemLifecycleController()
    runtime_config = ServiceRuntimeConfigParser(DEFAULT_RUNTIME_CONFIG).load()
    vehicle_settings = VehicleSettingsStore(default=runtime_config.vehicle)
    vehicle_configuration = vehicle_settings.load()
    telemetry_profile_publisher = ZeroMqPublisher(LOCAL_PUBLISHER_ENDPOINT)
    telemetry_profile_requests = AutomotiveTelemetryProfileRequestPublisher(
        telemetry_profile_publisher,
        source="orc-ui",
    )
    try:
        app = OrcUiApp(
            map_runtime=map_runtime,
            map_request_handler=map_camera.request_handler,
            lifecycle_handler=lifecycle,
            telemetry_profile_request=telemetry_profile_requests.publish,
            vehicle_configuration=vehicle_configuration,
            save_vehicle_configuration=vehicle_settings.save,
        )
    except Exception:
        telemetry_profile_publisher.close()
        map_camera.close()
        raise
    volume = SystemVolumeHandler(
        audio_controller=PipewireAudioController(),
        volume_ui=app,
        set_status=app.set_screen_status,
    )
    app.set_volume_request_handler(volume)
    state_ingress = StateIngressRuntime(
        schedule_ui=app.schedule_ui_callback,
        apply_vehicle_state=app.apply_vehicle_state,
        apply_trip_state=app.apply_trip_state,
        apply_position_state=app.apply_position_state,
        apply_attitude_state=app.apply_attitude_state,
    )
    fuel_config = runtime_config.automotive.fuel
    trip_tracker = TripTracker(
        fuel_model=FuelModel(
            engine_displacement_m3=fuel_config.engine_displacement_l / 1000.0,
            volumetric_efficiency=fuel_config.volumetric_efficiency,
        )
    )
    trip_publisher = ZeroMqPublisher(LOCAL_PUBLISHER_ENDPOINT)
    trip_runtime = TripRuntime(
        ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT),
        trip_publisher,
        tracker=trip_tracker,
        publish_source="orc-ui-trip-runtime",
    )
    return CoreComposition(
        app=app,
        map_runtime=map_runtime,
        map_camera=map_camera,
        state_ingress=state_ingress,
        trip_runtime=trip_runtime,
        trip_publisher=trip_publisher,
        telemetry_profile_publisher=telemetry_profile_publisher,
        lifecycle=lifecycle,
        volume=volume,
    )
