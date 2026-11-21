# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Config-driven radio profile and user-preset catalog."""

from __future__ import annotations

import json
import os
from pathlib import Path

from config.radio_config_manager import (RadioConfig, RadioModeConfig, RadioRangeConfig,
    RadioPresetConfig, RadioTileConfig, load_radio_config)
from controllers.radio.sdrforge_radio_catalog_client import SdrforgeRadioCatalogClient
from controllers.radio.sdrforge_readiness import SdrforgeNotReadyError

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_RADIO_ROOT = _PROJECT_ROOT / "config" / "radio"
_DEFAULT_USER_PRESETS = Path.home() / ".config" / "openroadcode" / "radio_presets.json"


from ui.radio.radio_profiles import RadioProfilePreset, RadioProfile


class RadioProfileCatalog:
    """Load installed radio profiles and merge persistent user presets."""

    def __init__(self, *, locale: str = "romeo", user_presets_path: str | Path | None = None) -> None:
        self._locale = locale
        self._user_presets_path = Path(user_presets_path or _DEFAULT_USER_PRESETS).expanduser()
        self._profiles: dict[str, RadioProfile] = {}
        self._remote_configs: dict[str, RadioConfig] = {}
        self._remote_enabled = os.environ.get("ORC_SDRFORGE_RADIO_CATALOG") == "1"
        self.reload()

    @property
    def profiles(self) -> tuple[RadioProfile, ...]:
        return tuple(self._profiles[key] for key in sorted(self._profiles))

    def profile(self, key: str) -> RadioProfile:
        try:
            return self._profiles[key]
        except KeyError as exc:
            raise ValueError(f"Unknown radio profile: {key}") from exc

    def profiles_for_group(self, group: str) -> tuple[RadioProfile, ...]:
        normalized = group.strip().upper()
        return tuple(profile for profile in self.profiles if profile.group == normalized)

    def config_for(self, key: str) -> RadioConfig:
        """Return SDRForge's authoritative profile or the legacy local config."""
        if key in self._remote_configs:
            return self._remote_configs[key]
        return load_radio_config(self.profile(key).config_path)

    def _load_remote(self) -> bool:
        if not self._remote_enabled:
            return False
        try:
            remote = SdrforgeRadioCatalogClient().profiles()
            if not remote:
                return False
            profiles: dict[str, RadioProfile] = {}
            configs: dict[str, RadioConfig] = {}
            for item in remote:
                mode = RadioModeConfig(item.mode_name, item.bandwidth, item.step_hz)
                presets = tuple(RadioProfilePreset(
                    p.label, p.frequency_hz, p.mode_name, p.bandwidth,
                    p.step_hz, p.user_defined,
                ) for p in item.presets)
                configs[item.key] = RadioConfig(
                    item.key, item.label, "", mode,
                    [RadioPresetConfig(p.label, p.frequency_hz,
                        RadioModeConfig(p.mode_name, p.bandwidth, p.step_hz))
                     for p in item.presets],
                    RadioTileConfig("Launch", "", ""),
                    RadioTileConfig("Radio", "", ""),
                    RadioRangeConfig(item.minimum_frequency_hz,
                        item.maximum_frequency_hz, item.start_frequency_hz),
                )
                profiles[item.key] = RadioProfile(
                    item.key, item.label, item.group,
                    _RADIO_ROOT / f"{item.key}.json", presets,
                )
        except (OSError, ValueError, KeyError, TypeError, IndexError, SdrforgeNotReadyError):
            return False
        self._remote_configs = configs
        self._profiles = profiles
        return True

    def reload(self) -> None:
        if self._load_remote():
            return
        self._remote_configs = {}
        user_presets = self._load_user_presets()
        profiles: dict[str, RadioProfile] = {}
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
            profiles[config.key] = RadioProfile(config.key, config.label, self._group_for_key(config.key), path, tuple(presets))
        self._profiles = profiles

    def add_user_preset(self, profile_key: str, *, label: str, frequency_hz: int, mode_name: str | None = None, bandwidth: int | None = None, step_hz: int | None = None) -> RadioProfilePreset:
        if self._remote_configs:
            remote = SdrforgeRadioCatalogClient()
            default = self.config_for(profile_key).default_mode
            mode = {"name": mode_name or default.name,
                    "bandwidth_hz": bandwidth if bandwidth is not None else default.bandwidth,
                    "step_hz": step_hz if step_hz is not None else default.step_hz}
            created = remote.create_preset(profile_key=profile_key, label=label,
                                          frequency_hz=frequency_hz, mode=mode)
            self.reload()
            selected = created["mode"]
            return RadioProfilePreset(created["label"], created["frequency_hz"],
                                      selected["name"], selected["bandwidth_hz"],
                                      selected["step_hz"], True)
        if not label.strip(): raise ValueError("preset label must not be empty")
        if frequency_hz <= 0: raise ValueError("preset frequency must be greater than zero")
        profile = self.profile(profile_key)
        config = load_radio_config(profile.config_path)
        data = self._load_user_presets()
        data.setdefault(profile_key, []).append({
            "label": label.strip(), "frequency_hz": int(frequency_hz),
            "mode": {"name": mode_name or config.default_mode.name,
                     "bandwidth": int(bandwidth if bandwidth is not None else config.default_mode.bandwidth),
                     "step_hz": int(step_hz if step_hz is not None else config.default_mode.step_hz)},
        })
        self._save_user_presets(data); self.reload()
        return self.profile(profile_key).presets[-1]

    def remove_user_preset(self, profile_key: str, *, label: str, frequency_hz: int) -> bool:
        if self._remote_configs:
            remote = SdrforgeRadioCatalogClient()
            selected = next((preset for profile in remote.profiles()
                             if profile.key == profile_key for preset in profile.presets
                             if preset.user_defined and preset.label == label
                             and preset.frequency_hz == frequency_hz), None)
            if selected is None:
                return False
            removed = remote.delete_preset(selected.id)
            if removed:
                self.reload()
            return removed
        data = self._load_user_presets(); entries = data.get(profile_key, [])
        remaining = [item for item in entries if not (str(item.get("label", "")) == label and int(item.get("frequency_hz", 0)) == int(frequency_hz))]
        if len(remaining) == len(entries): return False
        if remaining: data[profile_key] = remaining
        else: data.pop(profile_key, None)
        self._save_user_presets(data); self.reload(); return True

    def _profile_paths(self) -> tuple[Path, ...]:
        selected: dict[str, Path] = {}
        for directory in (_RADIO_ROOT / "common", _RADIO_ROOT / self._locale):
            if directory.exists():
                for path in sorted(directory.glob("*.json")): selected[path.stem] = path
        return tuple(selected[key] for key in sorted(selected))

    @staticmethod
    def _group_for_key(key: str) -> str:
        if key == "fm_radio": return "FM"
        if key == "weather_band": return "WEATHER"
        if key == "airband_am": return "AIR"
        if key.startswith("ham_"): return "HAM"
        return "SCANNER"

    @staticmethod
    def _preset_from_config(item) -> RadioProfilePreset:
        return RadioProfilePreset(item.label, item.frequency_hz, item.mode.name, item.mode.bandwidth, item.mode.step_hz, False)

    @staticmethod
    def _preset_from_user(item: dict, config: RadioConfig) -> RadioProfilePreset | None:
        try:
            mode = item.get("mode") or {}
            return RadioProfilePreset(str(item["label"]), int(item["frequency_hz"]), str(mode.get("name", config.default_mode.name)), int(mode.get("bandwidth", config.default_mode.bandwidth)), int(mode.get("step_hz", config.default_mode.step_hz)), True)
        except (KeyError, TypeError, ValueError): return None

    def _load_user_presets(self) -> dict[str, list[dict]]:
        if not self._user_presets_path.exists(): return {}
        try: raw = json.loads(self._user_presets_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): return {}
        if not isinstance(raw, dict): return {}
        return {str(key): [item for item in value if isinstance(item, dict)] for key, value in raw.items() if isinstance(value, list)}

    def _save_user_presets(self, data: dict[str, list[dict]]) -> None:
        self._user_presets_path.parent.mkdir(parents=True, exist_ok=True)
        self._user_presets_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
