# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Config-driven radio profile and user-preset catalog for orcUi."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from config.radio_config_manager import RadioConfig, load_radio_config

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_RADIO_ROOT = _PROJECT_ROOT / "config" / "radio"
_DEFAULT_USER_PRESETS = Path.home() / ".config" / "openroadcode" / "radio_presets.json"


@dataclass(frozen=True)
class OrcUiRadioPreset:
    label: str
    frequency_hz: int
    mode_name: str
    bandwidth: int
    step_hz: int
    user_defined: bool = False


@dataclass(frozen=True)
class OrcUiRadioProfile:
    key: str
    label: str
    group: str
    config_path: Path
    presets: tuple[OrcUiRadioPreset, ...]


class OrcUiRadioProfileCatalog:
    """Load installed radio profiles and merge persistent user presets."""

    def __init__(
        self,
        *,
        locale: str = "romeo",
        user_presets_path: str | Path | None = None,
    ) -> None:
        self._locale = locale
        self._user_presets_path = Path(user_presets_path or _DEFAULT_USER_PRESETS).expanduser()
        self._profiles: dict[str, OrcUiRadioProfile] = {}
        self.reload()

    @property
    def profiles(self) -> tuple[OrcUiRadioProfile, ...]:
        return tuple(self._profiles[key] for key in sorted(self._profiles))

    def profile(self, key: str) -> OrcUiRadioProfile:
        try:
            return self._profiles[key]
        except KeyError as exc:
            raise ValueError(f"Unknown radio profile: {key}") from exc

    def profiles_for_group(self, group: str) -> tuple[OrcUiRadioProfile, ...]:
        normalized = group.strip().upper()
        return tuple(profile for profile in self.profiles if profile.group == normalized)

    def reload(self) -> None:
        user_presets = self._load_user_presets()
        profiles: dict[str, OrcUiRadioProfile] = {}
        for path in self._profile_paths():
            try:
                config = load_radio_config(path)
            except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            presets = [self._preset_from_config(item) for item in config.presets]
            for item in user_presets.get(config.key, []):
                preset = self._preset_from_user(item, config)
                if preset is not None:
                    presets.append(preset)
            profiles[config.key] = OrcUiRadioProfile(
                key=config.key,
                label=config.label,
                group=self._group_for_key(config.key),
                config_path=path,
                presets=tuple(presets),
            )
        self._profiles = profiles

    def add_user_preset(
        self,
        profile_key: str,
        *,
        label: str,
        frequency_hz: int,
        mode_name: str | None = None,
        bandwidth: int | None = None,
        step_hz: int | None = None,
    ) -> OrcUiRadioPreset:
        if not label.strip():
            raise ValueError("preset label must not be empty")
        if frequency_hz <= 0:
            raise ValueError("preset frequency must be greater than zero")
        profile = self.profile(profile_key)
        config = load_radio_config(profile.config_path)
        mode = mode_name or config.default_mode.name
        bw = bandwidth if bandwidth is not None else config.default_mode.bandwidth
        step = step_hz if step_hz is not None else config.default_mode.step_hz
        data = self._load_user_presets()
        entries = data.setdefault(profile_key, [])
        entries.append(
            {
                "label": label.strip(),
                "frequency_hz": int(frequency_hz),
                "mode": {
                    "name": mode,
                    "bandwidth": int(bw),
                    "step_hz": int(step),
                },
            }
        )
        self._save_user_presets(data)
        self.reload()
        return self.profile(profile_key).presets[-1]

    def remove_user_preset(self, profile_key: str, *, label: str, frequency_hz: int) -> bool:
        data = self._load_user_presets()
        entries = data.get(profile_key, [])
        remaining = [
            item
            for item in entries
            if not (
                str(item.get("label", "")) == label
                and int(item.get("frequency_hz", 0)) == int(frequency_hz)
            )
        ]
        if len(remaining) == len(entries):
            return False
        if remaining:
            data[profile_key] = remaining
        else:
            data.pop(profile_key, None)
        self._save_user_presets(data)
        self.reload()
        return True

    def _profile_paths(self) -> tuple[Path, ...]:
        selected: dict[str, Path] = {}
        common_dir = _RADIO_ROOT / "common"
        if common_dir.exists():
            for path in sorted(common_dir.glob("*.json")):
                selected[path.stem] = path
        locale_dir = _RADIO_ROOT / self._locale
        if locale_dir.exists():
            for path in sorted(locale_dir.glob("*.json")):
                selected[path.stem] = path
        return tuple(selected[key] for key in sorted(selected))

    @staticmethod
    def _group_for_key(key: str) -> str:
        if key == "fm_radio":
            return "FM"
        if key == "weather_band":
            return "WEATHER"
        if key == "airband_am":
            return "AIR"
        if key.startswith("ham_"):
            return "HAM"
        return "SCANNER"

    @staticmethod
    def _preset_from_config(item) -> OrcUiRadioPreset:
        return OrcUiRadioPreset(
            label=item.label,
            frequency_hz=item.frequency_hz,
            mode_name=item.mode.name,
            bandwidth=item.mode.bandwidth,
            step_hz=item.mode.step_hz,
            user_defined=False,
        )

    @staticmethod
    def _preset_from_user(item: dict, config: RadioConfig) -> OrcUiRadioPreset | None:
        try:
            mode = item.get("mode") or {}
            return OrcUiRadioPreset(
                label=str(item["label"]),
                frequency_hz=int(item["frequency_hz"]),
                mode_name=str(mode.get("name", config.default_mode.name)),
                bandwidth=int(mode.get("bandwidth", config.default_mode.bandwidth)),
                step_hz=int(mode.get("step_hz", config.default_mode.step_hz)),
                user_defined=True,
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _load_user_presets(self) -> dict[str, list[dict]]:
        if not self._user_presets_path.exists():
            return {}
        try:
            raw = json.loads(self._user_presets_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {
            str(key): [item for item in value if isinstance(item, dict)]
            for key, value in raw.items()
            if isinstance(value, list)
        }

    def _save_user_presets(self, data: dict[str, list[dict]]) -> None:
        self._user_presets_path.parent.mkdir(parents=True, exist_ok=True)
        self._user_presets_path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
