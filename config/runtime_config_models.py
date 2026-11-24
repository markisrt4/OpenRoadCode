# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Typed values produced by the runtime configuration parser."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeDisplayConfig:
    """Configure the X display used by externally launched applications."""

    remote_display: str = ":2"
    auxiliary_display: str = ":0"
    media_display: str | None = None


@dataclass(frozen=True, slots=True)
class ImageCacheConfig:
    """Configure decoded-image memory and optional persistent source storage."""

    directory: Path | None = None
    max_entries: int = 24


@dataclass(frozen=True, slots=True)
class PositionCacheConfig:
    """Configure persistence of the last valid geographic fix."""

    enabled: bool = True
    directory: Path = Path.home() / ".cache" / "openroadcode" / "position"
    max_age_seconds: float = 604800.0


@dataclass(frozen=True, slots=True)
class AudioConfig:
    """Configure the preferred system audio output."""

    output: str = "auto"
    device_match: str | None = None


@dataclass(frozen=True, slots=True)
class RigctlConfig:
    """Configure the host and TCP port of the rigctl service."""

    host: str = "127.0.0.1"
    port: int = 4532


@dataclass(frozen=True, slots=True)
class SeesawEncoderConfig:
    """Configure one I2C Seesaw rotary encoder."""

    address: int
    reverse_direction: bool = False


@dataclass(frozen=True, slots=True)
class GpioEncoderConfig:
    """Configure one GPIO rotary encoder and its optional button."""

    pin_a: int
    pin_b: int
    button: int | None = None
    reverse_direction: bool = False


EncoderDeviceConfig = SeesawEncoderConfig | GpioEncoderConfig


@dataclass(frozen=True, slots=True)
class RotaryEncoderConfig:
    """Configure the ordered encoder devices and designated volume encoder."""

    devices: tuple[EncoderDeviceConfig, ...] = (
        SeesawEncoderConfig(address=0x36),
        SeesawEncoderConfig(address=0x37),
        SeesawEncoderConfig(address=0x38),
    )
    volume_index: int = 0


@dataclass(frozen=True, slots=True)
class KeyboardConfig:
    enabled: bool = False
    device_path: str | None = None


@dataclass(frozen=True, slots=True)
class PushButtonConfig:
    pin: int
    action: str
    active_low: bool = True
    debounce_seconds: float = 0.05


@dataclass(frozen=True, slots=True)
class InputConfig:
    """Contain runtime configuration for Car UI input devices."""

    rotary_encoders: RotaryEncoderConfig
    keyboard: KeyboardConfig = KeyboardConfig()
    push_buttons: tuple[PushButtonConfig, ...] = ()


@dataclass(frozen=True, slots=True)
class BarometricSensorConfig:
    """Configure the barometric sensor used by the Car UI."""

    driver: str = "bmp388"
    address: int = 0x77


@dataclass(frozen=True, slots=True)
class EnvironmentalConfig:
    """Contain runtime configuration for environmental sensors."""

    barometric_sensor: BarometricSensorConfig = BarometricSensorConfig()


@dataclass(frozen=True, slots=True)
class RadioStackConfig:
    """Configure one radio backend, profile, and optional launcher."""

    key: str
    config_path: Path
    backend: str
    launcher: str | None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Contain validated system-wide runtime composition."""

    runtime: RuntimeDisplayConfig
    rigctl: RigctlConfig
    input: InputConfig
    radios: tuple[RadioStackConfig, ...]
    environmental: EnvironmentalConfig = EnvironmentalConfig()
    image_cache: ImageCacheConfig = ImageCacheConfig()
    position_cache: PositionCacheConfig = PositionCacheConfig()
    audio: AudioConfig = AudioConfig()

    def enabled_radios(self) -> tuple[RadioStackConfig, ...]:
        """Return radio stacks enabled in this configuration."""
        return tuple(radio for radio in self.radios if radio.enabled)

    def radio(self, key: str) -> RadioStackConfig:
        """Return a radio stack by key.

        @param key Stable radio-stack identifier.
        @exception KeyError if the key is not configured.
        """
        for radio in self.radios:
            if radio.key == key:
                return radio
        raise KeyError(f"Unknown radio stack: {key}")
