from __future__ import annotations

from pathlib import Path
from typing import Callable

from apps.carUi.config.car_ui_runtime_config_parser import (
    CarUiRuntimeConfig,
    CarUiRuntimeConfigParser,
    RadioStackConfig,
)
from apps.carUi.runtime.radio_runtime import CarUiRuntime, RadioRuntime
from apps.carUi.runtime.radio_runtime_registry import RadioRuntimeRegistry
from apps.launchers.adsb_launcher import ADSBLauncher
from apps.launchers.sdrpp_launcher import SDRPPLauncher, SDRPPProfile
from apps.launchers.weather_dash_launcher import WeatherDashLauncher
from config.radio_config_manager import load_radio_config
from controllers.radio.radio_controller import RadioController
from controllers.radio.radio_types import RadioMode, RadioPreset, RadioRange
from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend
from controllers.sdr.sdr_resource_manager import SDRResourceManager
from protocols.rigctl.rigctl_client import RigctlClient


class CarUiRuntimeFactoryError(RuntimeError):
    """Raised when runtime composition cannot be completed."""


def create_car_ui_runtime(
    config_path: str | Path,
    *,
    project_root: str | Path | None = None,
) -> CarUiRuntime:
    """Parse TOML and assemble all enabled Car UI runtime components."""

    config = CarUiRuntimeConfigParser(
        config_path=config_path,
        project_root=project_root,
    ).load()

    return build_car_ui_runtime(config)


def build_car_ui_runtime(config: CarUiRuntimeConfig) -> CarUiRuntime:
    """Assemble a runtime from an already parsed configuration."""

    resource_manager = SDRResourceManager()
    runtimes: dict[str, RadioRuntime] = {}

    for stack in config.enabled_radios():
        runtime = _build_radio_runtime(
            stack=stack,
            config=config,
            resource_manager=resource_manager,
        )
        runtimes[runtime.key] = runtime

    adsb_launcher = None
    if config.auxiliary.adsb.enabled:
        adsb_launcher = ADSBLauncher(
            url=config.auxiliary.adsb.url,
            close_existing_display_apps=(
                config.auxiliary.adsb.close_existing_display_apps
            ),
        )

    weather_dash_launcher = None
    if config.auxiliary.weather_dashboard.enabled:
        weather_dash_launcher = WeatherDashLauncher()

    return CarUiRuntime(
        remote_display=config.runtime.remote_display,
        rotary_encoders=config.input.rotary_encoders,
        radios=RadioRuntimeRegistry(runtimes),
        adsb_launcher=adsb_launcher,
        weather_dash_launcher=weather_dash_launcher,
        sdr_resource_manager=resource_manager,
    )


def _build_radio_runtime(
    *,
    stack: RadioStackConfig,
    config: CarUiRuntimeConfig,
    resource_manager: SDRResourceManager,
) -> RadioRuntime:
    radio_config = load_radio_config(stack.config_path)

    backend = _build_backend(
        backend_type=stack.backend,
        config=config,
    )

    controller = RadioController(
        backend=backend,
        presets=tuple(
            RadioPreset(
                label=preset.label,
                frequency_hz=preset.frequency_hz,
                mode=_runtime_mode(preset.mode),
            )
            for preset in radio_config.presets
        ),
        default_mode=_runtime_mode(radio_config.default_mode),
        radio_range=_runtime_range(radio_config),
    )

    launcher = _build_launcher(
        launcher_type=stack.launcher,
        stack=stack,
        radio_config=radio_config,
        resource_manager=resource_manager,
    )

    return RadioRuntime(
        key=stack.key,
        config=radio_config,
        controller=controller,
        launcher=launcher,
    )


def _build_backend(
    *,
    backend_type: str,
    config: CarUiRuntimeConfig,
):
    builders: dict[str, Callable[[], object]] = {
        "rigctl": lambda: RigctlRadioBackend(
            RigctlClient(
                host=config.rigctl.host,
                port=config.rigctl.port,
            )
        ),
    }

    try:
        return builders[backend_type]()
    except KeyError as exc:
        supported = ", ".join(sorted(builders))
        raise CarUiRuntimeFactoryError(
            f"Unsupported radio backend '{backend_type}'. "
            f"Supported backends: {supported}"
        ) from exc


def _build_launcher(
    *,
    launcher_type: str | None,
    stack: RadioStackConfig,
    radio_config,
    resource_manager: SDRResourceManager,
):
    if launcher_type is None or launcher_type == "none":
        raise CarUiRuntimeFactoryError(
            f"Radio stack '{stack.key}' does not define a usable launcher"
        )

    if launcher_type != "sdrpp":
        raise CarUiRuntimeFactoryError(
            f"Unsupported radio launcher '{launcher_type}' "
            f"for stack '{stack.key}'"
        )

    profile = SDRPPProfile(
        name=getattr(radio_config, "label", stack.key),
        mode=radio_config.default_mode.name,
        step_hz=radio_config.default_mode.step_hz,
        start_frequency_hz=_profile_start_frequency(radio_config),
    )

    return SDRPPLauncher(
        profile=profile,
        resource_manager=resource_manager,
        owner_name=f"sdrpp_{stack.key}",
    )


def _runtime_mode(mode_config) -> RadioMode:
    return RadioMode(
        name=mode_config.name,
        bandwidth=mode_config.bandwidth,
        step_hz=mode_config.step_hz,
    )


def _runtime_range(radio_config) -> RadioRange | None:
    radio_range = getattr(radio_config, "radio_range", None)

    if radio_range is not None:
        return RadioRange(
            min_frequency_hz=radio_range.min_frequency_hz,
            max_frequency_hz=radio_range.max_frequency_hz,
            start_frequency_hz=radio_range.start_frequency_hz,
        )

    presets = tuple(getattr(radio_config, "presets", ()))
    if not presets:
        return None

    frequencies = tuple(preset.frequency_hz for preset in presets)
    return RadioRange(
        min_frequency_hz=min(frequencies),
        max_frequency_hz=max(frequencies),
        start_frequency_hz=frequencies[0],
    )


def _profile_start_frequency(radio_config) -> int | None:
    radio_range = _runtime_range(radio_config)
    if radio_range is not None:
        return radio_range.start_frequency_hz

    presets = tuple(getattr(radio_config, "presets", ()))
    if presets:
        return presets[0].frequency_hz

    return None
