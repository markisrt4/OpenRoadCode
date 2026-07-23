from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class RadioModeConfig:
    """Describe a demodulation mode loaded from radio configuration."""
    name: str
    bandwidth: int
    step_hz: int


@dataclass(frozen=True)
class RadioRangeConfig:
    """Define the valid and initial frequencies for a configured radio."""
    min_frequency_hz: int
    max_frequency_hz: int
    start_frequency_hz: int


@dataclass(frozen=True)
class RadioPresetConfig:
    """Describe a named preset and its demodulation mode."""
    label: str
    frequency_hz: int
    mode: RadioModeConfig

    @property
    def frequency_mhz(self) -> float:
        """Return the preset frequency in megahertz.

        @return Frequency converted from hertz to megahertz.
        """
        return self.frequency_hz / 1_000_000


@dataclass(frozen=True)
class RadioTileConfig:
    """Define the text displayed by a radio navigation tile."""
    label: str
    subtitle: str
    detail: str


@dataclass(frozen=True)
class RadioConfig:
    """Contain the complete configuration for one radio profile."""
    key: str
    label: str
    description: str
    default_mode: RadioModeConfig
    presets: list[RadioPresetConfig]
    launch: RadioTileConfig
    radio: RadioTileConfig
    radio_range: RadioRangeConfig | None = None


CONFIG_ROOT = Path(__file__).resolve().parent
RADIO_CONFIG_DIR = CONFIG_ROOT / "radio"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Radio config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Radio config must be a JSON object: {path}")

    return data


def _parse_mode(data: dict[str, Any]) -> RadioModeConfig:
    return RadioModeConfig(
        name=str(data["name"]),
        bandwidth=int(data["bandwidth"]),
        step_hz=int(data["step_hz"]),
    )


def _parse_range(data: dict[str, Any] | None) -> RadioRangeConfig | None:
    if not data:
        return None

    return RadioRangeConfig(
        min_frequency_hz=int(data["min_frequency_hz"]),
        max_frequency_hz=int(data["max_frequency_hz"]),
        start_frequency_hz=int(data["start_frequency_hz"]),
    )

def _parse_tile(data: dict[str, Any]) -> RadioTileConfig:
    return RadioTileConfig(
        label=str(data["label"]),
        subtitle=str(data["subtitle"]),
        detail=str(data["detail"]),
    )


def _parse_preset(data: dict[str, Any], default_mode: RadioModeConfig) -> RadioPresetConfig:
    mode = _parse_mode(data["mode"]) if "mode" in data else default_mode

    return RadioPresetConfig(
        label=str(data["label"]),
        frequency_hz=int(data["frequency_hz"]),
        mode=mode,
    )


def load_radio_config(path: str | Path) -> RadioConfig:
    """Load and validate a radio profile.

    @param path JSON configuration file to load.
    @return Parsed radio configuration.
    @raises FileNotFoundError if ``path`` does not exist.
    @raises ValueError if the file does not contain a JSON object.
    """
    path = Path(path)
    raw = _read_json(path)

    default_mode = _parse_mode(raw["default_mode"])
    presets = [
        _parse_preset(item, default_mode)
        for item in raw.get("presets", [])
    ]

    return RadioConfig(
        key=str(raw["key"]),
        label=str(raw["label"]),
        description=str(raw.get("description", "")),
        default_mode=default_mode,
        presets=presets,
        launch=_parse_tile(raw["launch"]),
        radio=_parse_tile(raw["radio"]),
        radio_range=_parse_range(raw.get("range")),
    )


def load_radio_config_by_name(name: str) -> RadioConfig:
    """Load a radio profile by its filename stem.

    @param name Filename without the ``.json`` suffix.
    @return Parsed radio configuration.
    """
    return load_radio_config(RADIO_CONFIG_DIR / f"{name}.json")


def load_fm_radio_config() -> RadioConfig:
    """Return the common FM broadcast radio configuration.

    @return Parsed ``fm_radio`` profile.
    """
    return load_radio_config_by_name("fm_radio")


def load_airband_am_config() -> RadioConfig:
    """Return the common AM airband radio configuration.

    @return Parsed ``airband_am`` profile.
    """
    return load_radio_config_by_name("airband_am")


def load_weather_band_config() -> RadioConfig:
    """Return the common NOAA weather-band configuration.

    @return Parsed ``weather_band`` profile.
    """
    return load_radio_config_by_name("weather_band")


def load_ham_radio_config() -> RadioConfig:
    """Return the common amateur-radio configuration.

    @return Parsed ``ham_radio`` profile.
    """
    return load_radio_config_by_name("ham_radio")


def load_radio_presets(name: str) -> list[RadioPresetConfig]:
    """Return presets from a named radio profile.

    @param name Radio configuration filename stem.
    @return Presets in configuration-file order.
    """
    return load_radio_config_by_name(name).presets


def list_radio_configs() -> list[str]:
    """Return the available radio profiles.

    @return Sorted configuration filename stems, or an empty list if the
        configuration directory does not exist.
    """
    if not RADIO_CONFIG_DIR.exists():
        return []

    return sorted(path.stem for path in RADIO_CONFIG_DIR.glob("*.json"))
