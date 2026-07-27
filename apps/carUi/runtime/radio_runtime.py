from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from apps.launchers.adsb_launcher import ADSBLauncher
from apps.launchers.app_launcher_if import AppLauncherIf
from apps.launchers.weather_dash_launcher import WeatherDashLauncher
from controllers.radio.radio_controller_if import RadioControllerIf
from apps.carUi.config.car_ui_runtime_config_parser import (
    LightingRuntimeConfig,
    RotaryEncoderConfig,
)

if TYPE_CHECKING:
    from apps.carUi.runtime.radio_runtime_registry import RadioRuntimeRegistry


@dataclass(frozen=True, slots=True)
class RadioRuntime:
    """Runtime objects for one configured radio stack."""

    key: str
    config: object
    controller: RadioControllerIf
    launcher: AppLauncherIf


@dataclass(frozen=True, slots=True)
class CarUiRuntime:
    """Application runtime dependencies assembled before the UI is created."""

    remote_display: str
    rotary_encoders: RotaryEncoderConfig
    radios: "RadioRuntimeRegistry"
    adsb_launcher: Optional[ADSBLauncher]
    weather_dash_launcher: Optional[WeatherDashLauncher]
    sdr_resource_manager: object
    lighting: LightingRuntimeConfig = LightingRuntimeConfig()
