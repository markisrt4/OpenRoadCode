from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Optional

from apps.launchers.adsb_launcher import ADSBLauncher
from apps.launchers.app_launcher_if import AppLauncherIf
from apps.launchers.weather_dash_launcher import WeatherDashLauncher
from controllers.radio.radio_controller_if import RadioControllerIf
from controllers.weather import OpenMeteoWeatherController
from config.runtime_config import (
    AudioConfig,
    ImageCacheConfig,
    InputConfig,
    PositionCacheConfig,
    RotaryEncoderConfig,
)

if TYPE_CHECKING:
    from apps.carUi.runtime.radio_runtime_registry import RadioRuntimeRegistry


LOGGER = logging.getLogger(__name__)


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
    auxiliary_display: str
    rotary_encoders: RotaryEncoderConfig
    radios: "RadioRuntimeRegistry"
    adsb_launcher: Optional[ADSBLauncher]
    weather_dash_launcher: Optional[WeatherDashLauncher]
    weather_controller: Optional[OpenMeteoWeatherController]
    sdr_resource_manager: object
    input_config: InputConfig | None = None
    image_cache: ImageCacheConfig = ImageCacheConfig()
    position_cache: PositionCacheConfig = PositionCacheConfig()
    audio: AudioConfig = AudioConfig()
    media_display: str | None = None

    def close(self) -> None:
        """Stop launchers and radio controllers owned by this runtime."""
        if self.weather_dash_launcher is not None:
            try:
                self.weather_dash_launcher.stop(self.auxiliary_display)
            except Exception:
                LOGGER.exception("Failed to stop weather dashboard")
        if self.adsb_launcher is not None:
            try:
                self.adsb_launcher.stop(self.auxiliary_display)
            except Exception:
                LOGGER.exception("Failed to stop ADS-B dashboard")
        for key, radio_runtime in self.radios.items():
            try:
                radio_runtime.controller.stop()
            except Exception:
                LOGGER.exception("Failed to stop radio runtime %s", key)
