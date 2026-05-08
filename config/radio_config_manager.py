from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RadioModeConfig:
    name: str
    bandwidth: int
    step_hz: int


@dataclass(frozen=True)
class RadioPresetConfig:
    label: str
    frequency_hz: int
    mode: RadioModeConfig

    @property
    def frequency_mhz(self) -> float:
        return self.frequency_hz / 1_000_000


@dataclass(frozen=True)
class RadioTileConfig:
    label: str
    subtitle: str
    detail: str


@dataclass(frozen=True)
class RadioConfig:
    key: str
    label: str
    description: str
    default_mode: RadioModeConfig
    presets: list[RadioPresetConfig]
    launch: RadioTileConfig
    radio: RadioTileConfig


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
    )


def load_radio_config_by_name(name: str) -> RadioConfig:
    return load_radio_config(RADIO_CONFIG_DIR / f"{name}.json")


def load_fm_radio_config() -> RadioConfig:
    return load_radio_config_by_name("fm_radio")


def load_airband_am_config() -> RadioConfig:
    return load_radio_config_by_name("airband_am")


def load_weather_band_config() -> RadioConfig:
    return load_radio_config_by_name("weather_band")


def load_ham_radio_config() -> RadioConfig:
    return load_radio_config_by_name("ham_radio")


def load_radio_presets(name: str) -> list[RadioPresetConfig]:
    return load_radio_config_by_name(name).presets


def list_radio_configs() -> list[str]:
    if not RADIO_CONFIG_DIR.exists():
        return []

    return sorted(path.stem for path in RADIO_CONFIG_DIR.glob("*.json"))
