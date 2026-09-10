# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the ORC shell with map, volume, and state-ingress infrastructure."""

from __future__ import annotations

from dataclasses import dataclass

from apps.orcUi.core_runtime import MapRuntime, StateIngressRuntime
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from controllers.audio import PipewireAudioController, SystemVolumeHandler
from controllers.system import SystemLifecycleController


@dataclass(slots=True)
class CoreComposition:
    """Own the shell-facing infrastructure for one ORC UI process."""

    app: OrcUiApp
    map_runtime: MapRuntime
    state_ingress: StateIngressRuntime
    lifecycle: SystemLifecycleController
    volume: SystemVolumeHandler

    def start(self) -> None:
        self.volume.refresh()
        self.state_ingress.start()

    def close(self) -> None:
        try:
            self.state_ingress.close()
        finally:
            self.map_runtime.stop()


def create_core_composition() -> CoreComposition:
    """Create the selected frontend shell and inject runtime-facing dependencies."""
    map_runtime = MapRuntime()
    lifecycle = SystemLifecycleController()
    app = OrcUiApp(
        map_runtime=map_runtime,
        lifecycle_handler=lifecycle,
    )
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
        state_ingress=state_ingress,
        lifecycle=lifecycle,
        volume=volume,
    )
