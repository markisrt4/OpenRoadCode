# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from config.runtime_config import RuntimeConfig, RuntimeConfigParser, RadioStackConfig
from config.application_config import ApplicationsConfig, ApplicationsConfigParser
from apps.carUi.runtime.car_ui_runtime import CarUiRuntime, RadioRuntime
from apps.carUi.runtime.radio_runtime_registry import RadioRuntimeRegistry
from apps.carUi.runtime.weather_location_provider import CarUiWeatherLocationProvider
from apps.launchers.adsb_launcher import ADSBLauncher
from apps.launchers.app_runtime_manager import AppRuntimeManager
from apps.launchers.browser_app_factory import BrowserApplicationFactory
from apps.launchers.sdrpp_launcher import SDRPPLauncher, SDRPPProfile
from apps.launchers.weather_dash_launcher import WeatherDashLauncher
from controllers.cache import PersistentCache
from controllers.weather import DEFAULT_WEATHER_CACHE_DIRECTORY, GpsdWeatherLocationProvider, OpenMeteoWeatherController, WeatherSnapshotCache
from controllers.navigation import PositionSnapshotCache
from config.radio_config_manager import load_radio_config
from controllers.radio.radio_controller import RadioController
from controllers.radio.radio_types import RadioMode, RadioPreset, RadioRange
from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend
from controllers.sdr.sdr_resource_manager import SDRResourceManager
from protocols.rigctl.rigctl_client import RigctlClient

DEFAULT_APPLICATION_CONFIG = Path(__file__).resolve().parents[3] / "config" / "applications.toml"


class CarUiRuntimeFactoryError(RuntimeError):
    """Raised when runtime composition cannot be completed."""


def create_car_ui_runtime(config_path: str | Path, *, project_root: str | Path | None = None, applications_config_path: str | Path | None = None) -> CarUiRuntime:
    """Parse TOML and assemble all enabled Car UI runtime components."""
    config = RuntimeConfigParser(config_path=config_path, project_root=project_root).load()
    applications = ApplicationsConfigParser(applications_config_path or DEFAULT_APPLICATION_CONFIG).load()
    return build_car_ui_runtime(config, applications_config=applications)


def build_car_ui_runtime(config: RuntimeConfig, *, applications_config: ApplicationsConfig | None = None) -> CarUiRuntime:
    """Assemble a runtime from already parsed system and application config."""
    resource_manager = SDRResourceManager()
    runtimes: dict[str, RadioRuntime] = {}
    for stack in config.enabled_radios():
        runtime = _build_radio_runtime(stack=stack, config=config, resource_manager=resource_manager)
        runtimes[runtime.key] = runtime

    auxiliary_display = os.getenv("CARUI_AUXILIARY_DISPLAY") or config.runtime.auxiliary_display
    app_runtime_manager = (
        AppRuntimeManager(applications_config, remote_display=auxiliary_display)
        if applications_config is not None
        else None
    )

    adsb_launcher = None
    if config.auxiliary.adsb.enabled:
        adsb_launcher = ADSBLauncher(url=config.auxiliary.adsb.url, close_existing_display_apps=config.auxiliary.adsb.close_existing_display_apps)

    weather_controller = None
    if applications_config is not None:
        weather_app = applications_config.app("weather")
        if weather_app.enabled:
            weather_cache = WeatherSnapshotCache(PersistentCache(DEFAULT_WEATHER_CACHE_DIRECTORY))
            weather_location_provider = GpsdWeatherLocationProvider()
            if config.position_cache.enabled:
                weather_location_provider = CarUiWeatherLocationProvider(
                    weather_location_provider,
                    PositionSnapshotCache(PersistentCache(config.position_cache.directory)),
                    max_age_seconds=config.position_cache.max_age_seconds,
                )
            weather_controller = OpenMeteoWeatherController(weather_cache, location_provider=weather_location_provider)
            browser = BrowserApplicationFactory(applications_config).create("weather")
            weather_launcher = WeatherDashLauncher(
                cache_directory=DEFAULT_WEATHER_CACHE_DIRECTORY,
                browser=browser,
            )
            app_runtime_manager.register("weather", weather_launcher)

    return CarUiRuntime(
        remote_display=config.runtime.remote_display,
        auxiliary_display=auxiliary_display,
        media_display=config.runtime.media_display,
        rotary_encoders=config.input.rotary_encoders,
        radios=RadioRuntimeRegistry(runtimes),
        adsb_launcher=adsb_launcher,
        weather_controller=weather_controller,
        sdr_resource_manager=resource_manager,
        app_runtime_manager=app_runtime_manager,
        input_config=config.input,
        image_cache=config.image_cache,
        position_cache=config.position_cache,
        audio=config.audio,
    )


def _build_radio_runtime(*, stack: RadioStackConfig, config: RuntimeConfig, resource_manager: SDRResourceManager) -> RadioRuntime:
    radio_config = load_radio_config(stack.config_path)
    backend = _build_backend(backend_type=stack.backend, config=config)
    controller = RadioController(
        backend=backend,
        presets=tuple(RadioPreset(label=preset.label, frequency_hz=preset.frequency_hz, mode=_runtime_mode(preset.mode)) for preset in radio_config.presets),
        default_mode=_runtime_mode(radio_config.default_mode),
        radio_range=_runtime_range(radio_config),
    )
    launcher = _build_launcher(launcher_type=stack.launcher, stack=stack, radio_config=radio_config, resource_manager=resource_manager)
    return RadioRuntime(key=stack.key, config=radio_config, controller=controller, launcher=launcher)


def _build_backend(*, backend_type: str, config: RuntimeConfig):
    builders: dict[str, Callable[[], object]] = {"rigctl": lambda: RigctlRadioBackend(RigctlClient(host=config.rigctl.host, port=config.rigctl.port))}
    try:
        return builders[backend_type]()
    except KeyError as exc:
        supported = ", ".join(sorted(builders))
        raise CarUiRuntimeFactoryError(f"Unsupported radio backend '{backend_type}'. Supported backends: {supported}") from exc


def _build_launcher(*, launcher_type: str | None, stack: RadioStackConfig, radio_config, resource_manager: SDRResourceManager):
    if launcher_type is None or launcher_type == "none":
        raise CarUiRuntimeFactoryError(f"Radio stack '{stack.key}' does not define a usable launcher")
    if launcher_type != "sdrpp":
        raise CarUiRuntimeFactoryError(f"Unsupported radio launcher '{launcher_type}' for stack '{stack.key}'")
    profile = SDRPPProfile(
        name=getattr(radio_config, "label", stack.key),
        mode=radio_config.default_mode.name,
        step_hz=radio_config.default_mode.step_hz,
        start_frequency_hz=_profile_start_frequency(radio_config),
    )
    return SDRPPLauncher(profile=profile, resource_manager=resource_manager, owner_name=f"sdrpp_{stack.key}")


def _runtime_mode(mode_config) -> RadioMode:
    return RadioMode(name=mode_config.name, bandwidth=mode_config.bandwidth, step_hz=mode_config.step_hz)


def _runtime_range(radio_config) -> RadioRange | None:
    radio_range = getattr(radio_config, "radio_range", None)
    if radio_range is not None:
        return RadioRange(min_frequency_hz=radio_range.min_frequency_hz, max_frequency_hz=radio_range.max_frequency_hz, start_frequency_hz=radio_range.start_frequency_hz)
    presets = tuple(getattr(radio_config, "presets", ()))
    if not presets:
        return None
    frequencies = tuple(preset.frequency_hz for preset in presets)
    return RadioRange(min_frequency_hz=min(frequencies), max_frequency_hz=max(frequencies), start_frequency_hz=frequencies[0])


def _profile_start_frequency(radio_config) -> int | None:
    radio_range = _runtime_range(radio_config)
    if radio_range is not None:
        return radio_range.start_frequency_hz
    presets = tuple(getattr(radio_config, "presets", ()))
    if presets:
        return presets[0].frequency_hz
    return None
