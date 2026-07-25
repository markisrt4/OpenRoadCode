from __future__ import annotations

import os
from pathlib import Path

from apps.carUi.runtime.radio_runtime_factory import create_car_ui_runtime
from apps.carUi.runtime.display_runtime import configure_display
from apps.carUi.runtime.lighting_runtime_factory import (
    create_lighting_controller,
)
from apps.carUi.runtime.spotify_runtime_factory import (
    create_spotify_controller,
)
from apps.carUi.runtime.rotary_encoder_runtime import (
    create_rotary_encoder_runtime,
)
from apps.carUi.splash_screen import show_startup_splash
from apps.carUi.uiControlPanel import UiControlPanel
from controllers.audio.pipewire_audio_controller import (
    PipewireAudioController,
)
from hardware_io.gps.gps_reader import GpsReader


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_PATH = (
    PROJECT_ROOT
    / "apps"
    / "carUi"
    / "config"
    / "car_ui_runtime.toml"
)


def main() -> None:
    try:
        configure_display()
    except RuntimeError as exc:
        raise SystemExit(f"[CarUI] {exc}") from exc

    show_startup_splash()

    runtime = create_car_ui_runtime(
        RUNTIME_CONFIG_PATH,
        project_root=PROJECT_ROOT,
    )

    gps_reader = GpsReader()
    audio_controller = PipewireAudioController()
    spotify_controller = create_spotify_controller()
    lighting_controller = create_lighting_controller(
        project_root=PROJECT_ROOT,
        address=os.getenv("CARUI_LIGHTING_ADDRESS"),
    )
    encoder_runtime = create_rotary_encoder_runtime(
        runtime.rotary_encoders
    )

    app = UiControlPanel(
        runtime=runtime,
        gps_device=gps_reader,
        lighting_controller=lighting_controller,
        audio_controller=audio_controller,
        spotify_controller=spotify_controller,
        rotary_encoders=encoder_runtime.encoders,
        volume_encoder_index=encoder_runtime.volume_index,
    )

    try:
        app.register_default_callbacks()
        app.start_encoder_events()
        app.start_gps_ui_updates()
        app.mainloop()
    finally:
        app.stop_encoder_events()
        gps_reader.close()
        lighting_controller.close()


if __name__ == "__main__":
    main()
