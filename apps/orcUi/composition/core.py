# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the ORC shell with map, volume, and state-ingress infrastructure."""

from __future__ import annotations

import math
from dataclasses import dataclass

from apps.orcUi.core_runtime import MapRuntime, StateIngressRuntime
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.map_camera_runtime import MapCameraRuntime
from apps.orcUi.shared_map_camera import (
    clear_shared_map_camera_runtime,
    install_shared_map_camera_runtime,
)
from controllers.audio import PipewireAudioController, SystemVolumeHandler
from controllers.system import SystemLifecycleController


@dataclass(slots=True)
class CoreComposition:
    """Own the shell-facing infrastructure for one ORC UI process."""

    app: OrcUiApp
    map_runtime: MapRuntime
    map_camera: MapCameraRuntime
    state_ingress: StateIngressRuntime
    lifecycle: SystemLifecycleController
    volume: SystemVolumeHandler

    def start(self) -> None:
        self.volume.refresh()
        self.map_camera.start()
        self.state_ingress.start()

    def close(self) -> None:
        try:
            self.state_ingress.close()
        finally:
            try:
                self.map_camera.close()
            finally:
                clear_shared_map_camera_runtime(self.map_camera)
                self.map_runtime.stop()


def create_core_composition() -> CoreComposition:
    """Create the selected frontend shell and inject runtime-facing dependencies."""
    map_runtime = MapRuntime()
    map_camera = MapCameraRuntime(
        zoom_level=16.5,
        pitch_rad=math.radians(45.0),
        follow_enabled=True,
    )
    install_shared_map_camera_runtime(map_camera)
    lifecycle = SystemLifecycleController()
    try:
        app = OrcUiApp(
            map_runtime=map_runtime,
            lifecycle_handler=lifecycle,
        )
    except Exception:
        clear_shared_map_camera_runtime(map_camera)
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
        apply_position_state=app.apply_position_state,
        apply_attitude_state=app.apply_attitude_state,
    )
    return CoreComposition(
        app=app,
        map_runtime=map_runtime,
        map_camera=map_camera,
        state_ingress=state_ingress,
        lifecycle=lifecycle,
        volume=volume,
    )
