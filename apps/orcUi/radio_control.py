# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose selectable ORC radio profiles for orcUi."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apps.orcUi.radio_profiles import OrcUiRadioPreset, OrcUiRadioProfileCatalog
from config.radio_config_manager import load_radio_config
from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend
from controllers.radio.radio_controller import RadioController, format_frequency
from controllers.radio.radio_types import RadioMode, RadioPreset, RadioRange
from protocols.rigctl.rigctl_client import RigctlClient


@dataclass(frozen=True)
class OrcUiRadioState:
    label: str
    frequency_hz: int
    mode_name: str
    profile_key: str
    profile_label: str
    rds: str | None = None


class OrcUiRadioControl:
    """Drive SDR++ through rigctl while switching config-driven profiles."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        *,
        catalog: OrcUiRadioProfileCatalog | None = None,
        client: RigctlClient | None = None,
    ) -> None:
        self._catalog = catalog or OrcUiRadioProfileCatalog()
        self._client = client or RigctlClient()
        self._radio: RadioController
        self._profile_key = ""
        if config_path is not None:
            config = load_radio_config(config_path)
            self._profile_key = config.key
            self._radio = self._build_controller(config)
        else:
            initial = "fm_radio" if any(p.key == "fm_radio" for p in self._catalog.profiles) else self._catalog.profiles[0].key
            self.select_profile(initial, start=False)

    @property
    def catalog(self) -> OrcUiRadioProfileCatalog:
        return self._catalog

    @property
    def active_profile_key(self) -> str:
        return self._profile_key

    @property
    def state(self) -> OrcUiRadioState:
        frequency_hz = self._radio.current_frequency_hz
        preset = self._matching_preset(frequency_hz)
        profile = self._catalog.profile(self._profile_key)
        rds = None
        if self._radio.is_started and self._profile_key == "fm_radio":
            try:
                rds = self._radio.get_rds()
            except (OSError, RuntimeError, ValueError):
                rds = None
        return OrcUiRadioState(
            label=preset.label if preset is not None else format_frequency(frequency_hz),
            frequency_hz=frequency_hz,
            mode_name=self._radio.current_mode.name,
            profile_key=self._profile_key,
            profile_label=profile.label,
            rds=rds,
        )

    def select_profile(self, profile_key: str, *, start: bool = True) -> OrcUiRadioState:
        profile = self._catalog.profile(profile_key)
        was_started = getattr(self, "_radio", None) is not None and self._radio.is_started
        if was_started:
            self._radio.stop()
        config = load_radio_config(profile.config_path)
        self._radio = self._build_controller(config)
        self._profile_key = profile_key
        if start or was_started:
            self._radio.start()
        return self.state

    def tune_preset(self, preset: OrcUiRadioPreset) -> OrcUiRadioState:
        domain_preset = RadioPreset(
            label=preset.label,
            frequency_hz=preset.frequency_hz,
            mode=RadioMode(preset.mode_name, preset.bandwidth, preset.step_hz),
        )
        self._ensure_started()
        self._radio.tune_preset(domain_preset)
        return self.state

    def next_preset(self) -> OrcUiRadioState:
        self._ensure_started(); self._radio.next_preset(); return self.state

    def previous_preset(self) -> OrcUiRadioState:
        self._ensure_started(); self._radio.previous_preset(); return self.state

    def tune_up(self) -> OrcUiRadioState:
        self._ensure_started(); self._radio.frequency_up(); return self.state

    def tune_down(self) -> OrcUiRadioState:
        self._ensure_started(); self._radio.frequency_down(); return self.state

    def refresh(self) -> OrcUiRadioState:
        if self._radio.is_started:
            self._radio.refresh_frequency()
        return self.state

    def _ensure_started(self) -> None:
        if not self._radio.is_started:
            self._radio.start()

    def _build_controller(self, config) -> RadioController:
        presets = [
            RadioPreset(
                label=item.label,
                frequency_hz=item.frequency_hz,
                mode=RadioMode(item.mode.name, item.mode.bandwidth, item.mode.step_hz),
            )
            for item in config.presets
        ]
        # Include persistent user presets in the controller's quick-cycle list.
        try:
            profile = self._catalog.profile(config.key)
            shipped = {(item.label, item.frequency_hz) for item in presets}
            for item in profile.presets:
                if (item.label, item.frequency_hz) in shipped:
                    continue
                presets.append(RadioPreset(item.label, item.frequency_hz, RadioMode(item.mode_name, item.bandwidth, item.step_hz)))
        except ValueError:
            pass
        default_mode = RadioMode(config.default_mode.name, config.default_mode.bandwidth, config.default_mode.step_hz)
        radio_range = None
        if config.radio_range is not None:
            radio_range = RadioRange(
                config.radio_range.min_frequency_hz,
                config.radio_range.max_frequency_hz,
                config.radio_range.start_frequency_hz,
            )
        return RadioController(
            backend=RigctlRadioBackend(self._client),
            presets=presets,
            default_mode=default_mode,
            radio_range=radio_range,
        )

    def _matching_preset(self, frequency_hz: int) -> RadioPreset | None:
        for preset in self._radio.presets:
            if preset.frequency_hz == frequency_hz:
                return preset
        return None
