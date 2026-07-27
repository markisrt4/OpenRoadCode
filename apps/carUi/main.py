from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from apps.carUi.runtime.display_runtime import configure_display
from apps.carUi.runtime.lighting_runtime_factory import (
    create_lighting_controller,
)
from apps.carUi.runtime.radio_runtime import CarUiRuntime
from apps.carUi.runtime.radio_runtime_factory import create_car_ui_runtime
from apps.carUi.runtime.spotify_runtime_factory import (
    create_spotify_controller,
)
from apps.carUi.splash_screen import (
    StartupItem,
    StartupState,
    StartupStatusCallback,
    create_startup_splash,
    splash_enabled,
)
from apps.carUi.uiControlPanel import UiControlPanel
from apps.common.uiTheme.uiTheme import CAR_UI_THEME
from controllers.audio.audio_controller_if import AudioControllerIf
from controllers.audio.pipewire_audio_controller import (
    PipewireAudioController,
)
from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.spotify import SpotifyControllerIf
from hardware_io.gps.gps_reader import GpsReader

from collections.abc import Sequence
from hardware_io.rotary_encoder import RotaryEncoderIf

from apps.carUi.runtime.rotary_encoder_runtime import (
    create_rotary_encoder_runtime,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_PATH = (
    PROJECT_ROOT
    / "apps"
    / "carUi"
    / "config"
    / "car_ui_runtime.toml"
)

STARTUP_ITEMS = (
    StartupItem("display", "Display"),
    StartupItem("runtime", "Runtime configuration"),
    StartupItem("gps", "GPS receiver"),
    StartupItem("audio", "Audio"),
    StartupItem("spotify", "Spotify"),
    StartupItem("lighting", "Lighting"),
    StartupItem("encoders", "Rotary controls"),
)


@dataclass
class ApplicationDependencies:
    runtime: CarUiRuntime
    gps_reader: GpsReader
    audio_controller: AudioControllerIf
    spotify_controller: SpotifyControllerIf
    lighting_controller: LightingControllerIf
    rotary_encoders: Sequence[RotaryEncoderIf]
    volume_encoder_index: int

    def close(self) -> None:
        self.gps_reader.close()
        self.lighting_controller.close()


def main() -> None:
    try:
        configure_display()
    except RuntimeError as exc:
        raise SystemExit(f"[CarUI] {exc}") from exc

    app: UiControlPanel | None = None
    dependencies: ApplicationDependencies | None = None

    try:
        if splash_enabled():
            splash = create_startup_splash(STARTUP_ITEMS)
            dependencies = splash.run(_initialize_dependencies)
        else:
            dependencies = _initialize_dependencies(_log_startup_status)

        app = UiControlPanel(
            runtime=dependencies.runtime,
            gps_device=dependencies.gps_reader,
            lighting_controller=dependencies.lighting_controller,
            audio_controller=dependencies.audio_controller,
            spotify_controller=dependencies.spotify_controller,
            rotary_encoders=dependencies.rotary_encoders,
            volume_encoder_index=dependencies.volume_encoder_index,
        )
        app.register_default_callbacks()
        app.start_encoder_events()
        app.start_gps_ui_updates()
        app.mainloop()
    except KeyboardInterrupt:
        print("\n[CarUI] Stopped")
    finally:
        try:
            if app is not None:
                app.close()
        finally:
            if dependencies is not None:
                dependencies.close()


def _initialize_dependencies(
    report: StartupStatusCallback,
) -> ApplicationDependencies:
    runtime: CarUiRuntime | None = None
    gps_reader: GpsReader | None = None
    audio_controller: AudioControllerIf | None = None
    spotify_controller: SpotifyControllerIf | None = None
    lighting_controller: LightingControllerIf | None = None

    try:
        report("display", StartupState.READY, "Display configured")

        report("runtime", StartupState.STARTING, "Loading configuration")
        runtime = create_car_ui_runtime(
            RUNTIME_CONFIG_PATH,
            project_root=PROJECT_ROOT,
        )
        report("runtime", StartupState.READY, "Configuration loaded")
        report("encoders", StartupState.STARTING, "Loading rotary controls")

        encoder_runtime = create_rotary_encoder_runtime(
            runtime.rotary_encoders,
        )

        report(
            "encoders",
            StartupState.READY,
            f"{len(encoder_runtime.encoders)} controls ready",
        )
        report("gps", StartupState.STARTING, "Opening receiver")
        gps_reader = GpsReader()
        report("gps", StartupState.READY, "Receiver available")

        report("audio", StartupState.STARTING, "Connecting to PipeWire")
        audio_controller = PipewireAudioController(
            steps=CAR_UI_THEME["layout"]["volume_steps"],
        )
        report("audio", StartupState.READY, "Audio controller ready")

        report("spotify", StartupState.STARTING, "Loading controller")
        spotify_controller = create_spotify_controller()
        report("spotify", StartupState.READY, "Controller ready")

        report("lighting", StartupState.STARTING, "Loading controller")
        lighting_controller = create_lighting_controller(
            project_root=PROJECT_ROOT,
            backend=runtime.lighting.backend,
            address=os.getenv("CARUI_LIGHTING_ADDRESS"),
        )
        report("lighting", StartupState.READY, "Controller ready")

        return ApplicationDependencies(
            runtime=runtime,
            gps_reader=gps_reader,
            audio_controller=audio_controller,
            spotify_controller=spotify_controller,
            lighting_controller=lighting_controller,
            rotary_encoders=encoder_runtime.encoders,
            volume_encoder_index=encoder_runtime.volume_index,
        )

    except BaseException:
        if gps_reader is not None:
            gps_reader.close()
        if lighting_controller is not None:
            lighting_controller.close()
        raise


def _log_startup_status(
    key: str,
    state: StartupState,
    detail: str,
) -> None:
    print(f"[Startup] {key}: {state.name.lower()} - {detail}")


if __name__ == "__main__":
    main()
