# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Car UI startup policy and dependency initialization."""

from __future__ import annotations

import os
from contextlib import ExitStack
from pathlib import Path
from config.runtime_target import RuntimeTarget, detect_runtime_target

from apps.carUi.car_ui_dependencies import CarUiDependencies
from apps.carUi.runtime.car_ui_runtime_factory import create_car_ui_runtime
from apps.carUi.runtime.lighting_runtime_factory import create_lighting_controller
from apps.carUi.runtime.input_device_runtime import InputDeviceRuntime, create_input_device_runtime
from apps.carUi.runtime.rotary_encoder_runtime import create_rotary_encoder_runtime
from apps.carUi.runtime.spotify_runtime_factory import create_spotify_controller
from apps.common.uiTheme.uiTheme import CAR_UI_THEME
from apps.carUi.runtime.audio_runtime_factory import create_audio_controller
from controllers.image import ImageCache
from controllers.lyrics import LrclibLyricsClient
from controllers.video import MusicVideoController, NetflixPlayer, YouTubeMusicVideo, YouTubePlayer
from frontends.tk.system import StartupItem, StartupSplash, StartupState, StartupStatusCallback


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_PATH = PROJECT_ROOT / "config" / "runtime.toml"
TERMUX_RUNTIME_CONFIG_PATH = PROJECT_ROOT / "config" / "runtime.termux.toml"
APPLICATIONS_CONFIG_PATH = PROJECT_ROOT / "config" / "applications.toml"
TERMUX_APPLICATIONS_CONFIG_PATH = PROJECT_ROOT / "config" / "applications.termux.toml"
SPLASH_IMAGE_PATH = Path(__file__).parent / "assets" / "openroadcode-splash.png"

STARTUP_ITEMS = (
    StartupItem("display", "Display"),
    StartupItem("runtime", "Runtime configuration"),
    StartupItem("telemetry", "Telemetry bus"),
    StartupItem("audio", "Audio"),
    StartupItem("spotify", "Spotify"),
    StartupItem("lighting", "Lighting"),
    StartupItem("input", "Input devices"),
)


def initialize_car_ui_dependencies() -> CarUiDependencies:
    if car_ui_splash_enabled():
        return create_car_ui_startup_splash().run(build_car_ui_dependencies)
    return build_car_ui_dependencies(log_startup_status)


def create_car_ui_startup_splash() -> StartupSplash[CarUiDependencies]:
    return StartupSplash(
        items=STARTUP_ITEMS,
        image_path=SPLASH_IMAGE_PATH,
        window_title="OpenRoadCode",
        heading="OPEN ROAD CODE",
        subtitle="INITIALIZING VEHICLE SYSTEMS",
        footer="OPEN SOURCE SOFTWARE FOR THE ROAD",
        fade_ms=_env_int("CARUI_SPLASH_FADE_MS", 500),
        completion_hold_ms=_env_int("CARUI_SPLASH_COMPLETION_HOLD_MS", 350),
        failure_hold_ms=_env_int("CARUI_SPLASH_FAILURE_HOLD_MS", 2500),
        fullscreen=_env_bool("CARUI_SPLASH_FULLSCREEN", _env_bool("CARUI_FULLSCREEN", False)),
        geometry=os.getenv("CARUI_GEOMETRY", "1024x600"),
    )


def _is_termux() -> bool:
    prefix = os.getenv("PREFIX", "")
    return bool(os.getenv("TERMUX_VERSION")) or prefix.startswith("/data/data/com.termux/")


def resolve_config_paths() -> tuple[Path, Path]:
    """Return matching system and application configuration profiles."""
    runtime_override = os.getenv("OPENROAD_RUNTIME_CONFIG")
    applications_override = os.getenv("OPENROAD_APPLICATIONS_CONFIG")
    runtime_path = Path(runtime_override).expanduser() if runtime_override else (
        TERMUX_RUNTIME_CONFIG_PATH if _is_termux() else RUNTIME_CONFIG_PATH
    )
    applications_path = Path(applications_override).expanduser() if applications_override else (
        TERMUX_APPLICATIONS_CONFIG_PATH if _is_termux() else APPLICATIONS_CONFIG_PATH
    )
    return runtime_path, applications_path


def car_ui_splash_enabled() -> bool:
    """Return whether the startup splash should be used.

    Termux defaults the splash off because creating a splash ``Tk`` root and
    then a second application ``Tk`` root can leave Tcl image/interpreter
    resources with unsafe destruction ordering on Android/Termux Python builds.
    ``CARUI_SPLASH`` remains an explicit override on every platform.
    """
    if "CARUI_SPLASH" in os.environ:
        return _env_bool("CARUI_SPLASH", True)
    return not _is_termux()


def build_car_ui_dependencies(report: StartupStatusCallback) -> CarUiDependencies:
    """Construct resources owned by Car UI; telemetry producers live elsewhere."""
    with ExitStack() as cleanup:
        report("display", StartupState.READY, "Display configured")
        report("runtime", StartupState.STARTING, "Loading configuration")
        runtime_config_path, applications_config_path = resolve_config_paths()
        runtime = create_car_ui_runtime(
            runtime_config_path,
            project_root=PROJECT_ROOT,
            applications_config_path=applications_config_path,
        )
        cleanup.callback(runtime.close)
        runtime.start_background_apps()
        report("runtime", StartupState.READY, "Configuration loaded")
        report("telemetry", StartupState.READY, "Vehicle and navigation state provided by message bus")

        report("input", StartupState.STARTING, "Loading input devices")
        encoder_runtime = create_rotary_encoder_runtime(runtime.rotary_encoders)
        input_config = getattr(runtime, "input_config", None)
        input_devices = create_input_device_runtime(input_config) if input_config is not None else InputDeviceRuntime()
        for encoder in encoder_runtime.encoders:
            cleanup.callback(encoder.stop)
        report("input", StartupState.READY, f"{len(encoder_runtime.encoders)} rotary controls ready")

        report("audio", StartupState.STARTING, "Connecting to PipeWire")
        runtime_target = detect_runtime_target()
        audio_controller = create_audio_controller(steps=CAR_UI_THEME["layout"]["volume_steps"], config=runtime.audio, target=runtime_target)
        report("audio", StartupState.READY, "Audio controller ready")

        report("spotify", StartupState.STARTING, "Loading controller")
        spotify_controller = create_spotify_controller()
        spotify_image_cache = ImageCache(max_entries=runtime.image_cache.max_entries, cache_directory=runtime.image_cache.directory)
        spotify_lyrics_client = LrclibLyricsClient()
        spotify_music_video_controller = MusicVideoController(
            spotify_controller=spotify_controller,
            music_video=YouTubeMusicVideo(fullscreen=True, software_rendering=runtime_target is RuntimeTarget.LINUX_DEV),
        )
        cleanup.callback(spotify_music_video_controller.stop_video)
        software_rendering = runtime_target is RuntimeTarget.LINUX_DEV
        netflix_player = NetflixPlayer(software_rendering=software_rendering)
        youtube_player = YouTubePlayer(software_rendering=software_rendering)
        cleanup.callback(netflix_player.stop)
        cleanup.callback(youtube_player.stop)
        report("spotify", StartupState.READY, "Controller ready")

        report("lighting", StartupState.STARTING, "Loading controller")
        lighting_controller = create_lighting_controller(project_root=PROJECT_ROOT, address=os.getenv("CARUI_LIGHTING_ADDRESS"))
        cleanup.callback(lighting_controller.close)
        report("lighting", StartupState.READY, "Controller ready")

        dependencies = CarUiDependencies(
            runtime=runtime,
            audio_controller=audio_controller,
            spotify_controller=spotify_controller,
            spotify_image_cache=spotify_image_cache,
            spotify_lyrics_client=spotify_lyrics_client,
            spotify_music_video_controller=spotify_music_video_controller,
            netflix_player=netflix_player,
            youtube_player=youtube_player,
            lighting_controller=lighting_controller,
            rotary_encoders=encoder_runtime.encoders,
            volume_encoder_index=encoder_runtime.volume_index,
            media_display=resolve_media_display(runtime_target, runtime.remote_display, runtime.media_display),
            keyboards=input_devices.keyboards,
            push_buttons=input_devices.push_buttons,
            push_button_actions=input_devices.push_button_actions,
        )
        cleanup.pop_all()
        return dependencies


def resolve_media_display(target: RuntimeTarget, configured_display: str, media_display: str | None = None) -> str:
    explicit_display = os.getenv("CARUI_MEDIA_DISPLAY") or media_display
    if explicit_display:
        return explicit_display
    if target is RuntimeTarget.LINUX_DEV:
        return os.getenv("DISPLAY") or configured_display
    return configured_display


def log_startup_status(key: str, state: StartupState, detail: str) -> None:
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
