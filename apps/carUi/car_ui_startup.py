"""Car UI startup policy and dependency initialization."""

from __future__ import annotations

import os
from contextlib import ExitStack
from pathlib import Path

from apps.carUi.car_ui_dependencies import CarUiDependencies
from apps.carUi.runtime.car_ui_runtime_factory import create_car_ui_runtime
from apps.carUi.runtime.lighting_runtime_factory import (
    create_lighting_controller,
)
from apps.carUi.runtime.position_source_factory import create_position_source
from apps.carUi.runtime.input_device_runtime import InputDeviceRuntime, create_input_device_runtime
from apps.carUi.runtime.rotary_encoder_runtime import (
    create_rotary_encoder_runtime,
)
from apps.carUi.runtime.spotify_runtime_factory import (
    create_spotify_controller,
)
from apps.common.uiTheme.uiTheme import CAR_UI_THEME
from controllers.audio.pipewire_audio_controller import (
    PipewireAudioController,
)
from controllers.navigation import Mpu6050NavigationAdapter, NavigationController
from frontends.tk.system import (
    StartupItem,
    StartupSplash,
    StartupState,
    StartupStatusCallback,
)
from hardware_io.imu import Mpu6050Imu


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_PATH = PROJECT_ROOT / "config" / "runtime.toml"
SPLASH_IMAGE_PATH = (
    Path(__file__).parent / "assets" / "openroadcode-splash.png"
)

STARTUP_ITEMS = (
    StartupItem("display", "Display"),
    StartupItem("runtime", "Runtime configuration"),
    StartupItem("position", "Position source"),
    StartupItem("navigation", "Motion navigation"),
    StartupItem("audio", "Audio"),
    StartupItem("spotify", "Spotify"),
    StartupItem("lighting", "Lighting"),
    StartupItem("input", "Input devices"),
)


def initialize_car_ui_dependencies() -> CarUiDependencies:
    """Build dependencies using the configured startup presentation."""
    if car_ui_splash_enabled():
        return create_car_ui_startup_splash().run(build_car_ui_dependencies)
    return build_car_ui_dependencies(log_startup_status)


def create_car_ui_startup_splash() -> StartupSplash[CarUiDependencies]:
    """Create the branded splash using Car UI environment policy."""
    return StartupSplash(
        items=STARTUP_ITEMS,
        image_path=SPLASH_IMAGE_PATH,
        window_title="OpenRoadCode",
        heading="OPEN ROAD CODE",
        subtitle="INITIALIZING VEHICLE SYSTEMS",
        footer="OPEN SOURCE SOFTWARE FOR THE ROAD",
        fade_ms=_env_int("CARUI_SPLASH_FADE_MS", 500),
        completion_hold_ms=_env_int(
            "CARUI_SPLASH_COMPLETION_HOLD_MS", 350
        ),
        failure_hold_ms=_env_int("CARUI_SPLASH_FAILURE_HOLD_MS", 2500),
        fullscreen=_env_bool(
            "CARUI_SPLASH_FULLSCREEN",
            _env_bool("CARUI_FULLSCREEN", False),
        ),
        geometry=os.getenv("CARUI_GEOMETRY", "1024x600"),
    )


def car_ui_splash_enabled() -> bool:
    return _env_bool("CARUI_SPLASH", True)


def build_car_ui_dependencies(
    report: StartupStatusCallback,
) -> CarUiDependencies:
    """Construct the controllers and hardware selected by Car UI."""
    with ExitStack() as cleanup:
        report("display", StartupState.READY, "Display configured")
        report("runtime", StartupState.STARTING, "Loading configuration")
        runtime = create_car_ui_runtime(
            RUNTIME_CONFIG_PATH,
            project_root=PROJECT_ROOT,
        )
        cleanup.callback(runtime.close)
        report("runtime", StartupState.READY, "Configuration loaded")
        report("input", StartupState.STARTING, "Loading input devices")
        encoder_runtime = create_rotary_encoder_runtime(runtime.rotary_encoders)
        input_config = getattr(runtime, "input_config", None)
        input_devices = (
            create_input_device_runtime(input_config)
            if input_config is not None
            else InputDeviceRuntime()
        )
        for encoder in encoder_runtime.encoders:
            cleanup.callback(encoder.stop)
        report(
            "input",
            StartupState.READY,
            f"{len(encoder_runtime.encoders)} rotary controls ready",
        )

        report("position", StartupState.STARTING, "Opening position source")
        position_source = create_position_source()
        cleanup.callback(position_source.stop)
        report("position", StartupState.READY, "Position source available")

        report("navigation", StartupState.STARTING, "Preparing motion sensor")
        navigation_controller = NavigationController(
            sensor=Mpu6050NavigationAdapter(
                Mpu6050Imu(
                    address=_env_int(
                        "CARUI_IMU_ADDRESS",
                        Mpu6050Imu.DEFAULT_ADDRESS,
                    )
                )
            ),
            filter_time_constant_s=float(
                os.getenv("CARUI_IMU_FILTER_TIME_CONSTANT", "0.5")
            ),
        )
        cleanup.callback(navigation_controller.stop)
        report("navigation", StartupState.READY, "Motion navigation prepared")

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
            address=os.getenv("CARUI_LIGHTING_ADDRESS"),
        )
        cleanup.callback(lighting_controller.close)
        report("lighting", StartupState.READY, "Controller ready")

        dependencies = CarUiDependencies(
            runtime=runtime,
            position_source=position_source,
            audio_controller=audio_controller,
            spotify_controller=spotify_controller,
            lighting_controller=lighting_controller,
            rotary_encoders=encoder_runtime.encoders,
            volume_encoder_index=encoder_runtime.volume_index,
            navigation_controller=navigation_controller,
            keyboards=input_devices.keyboards,
            push_buttons=input_devices.push_buttons,
            push_button_actions=input_devices.push_button_actions,
        )
        cleanup.pop_all()
        return dependencies


def log_startup_status(
    key: str,
    state: StartupState,
    detail: str,
) -> None:
    print(f"[Startup] {key}: {state.name.lower()} - {detail}")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value, 0)
    except ValueError:
        return default
