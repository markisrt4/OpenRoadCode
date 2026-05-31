from typing import Optional

from modules.radio.radio_types import RadioMode, RadioPreset, RadioRange


class RadioController:
    def __init__(
        self,
        backend,
        presets: list[RadioPreset],
        default_mode: RadioMode,
        radio_range: Optional[RadioRange] = None,
    ) -> None:
        self.backend = backend
        self.presets = presets
        self.default_mode = default_mode
        self.radio_range = radio_range

        self.current_preset_index = 0
        self.current_frequency_hz = (
            radio_range.start_frequency_hz
            if radio_range is not None
            else presets[0].frequency_hz if presets else 0
        )

    def start(self) -> int:
        self.backend.start()

        self.backend.set_mode(
            self.default_mode.name,
            self.default_mode.bandwidth,
        )

        if self.radio_range is not None:
            self.current_frequency_hz = self.radio_range.start_frequency_hz

        self.backend.set_frequency(self.current_frequency_hz)

        return self.current_frequency_hz

    def stop(self) -> None:
        self.backend.stop()

    def tune_preset(self, preset: RadioPreset) -> RadioPreset:
        self.backend.set_mode(
            preset.mode.name,
            preset.mode.bandwidth,
        )
        self.backend.set_frequency(preset.frequency_hz)

        self.current_frequency_hz = preset.frequency_hz

        try:
            self.current_preset_index = self.presets.index(preset)
        except ValueError:
            pass

        return preset

    def tune_preset_index(self, index: int) -> RadioPreset:
        if not self.presets:
            raise ValueError("No radio presets configured")

        wrapped_index = index % len(self.presets)
        self.current_preset_index = wrapped_index
        return self.tune_preset(self.presets[wrapped_index])

    def next_preset(self) -> RadioPreset:
        return self.tune_preset_index(self.current_preset_index + 1)

    def previous_preset(self) -> RadioPreset:
        return self.tune_preset_index(self.current_preset_index - 1)

    def frequency_up(self, delta_hz: Optional[int] = None) -> int:
        step = delta_hz or self.default_mode.step_hz
        return self.set_frequency(self.current_frequency_hz + step)

    def frequency_down(self, delta_hz: Optional[int] = None) -> int:
        step = delta_hz or self.default_mode.step_hz
        return self.set_frequency(self.current_frequency_hz - step)

    def set_frequency(self, frequency_hz: int) -> int:
        frequency_hz = self._wrap_frequency(frequency_hz)
        self.backend.set_frequency(frequency_hz)
        self.current_frequency_hz = frequency_hz
        return frequency_hz

    def _wrap_frequency(self, frequency_hz: int) -> int:
        if self.radio_range is None:
            return frequency_hz

        if frequency_hz > self.radio_range.max_frequency_hz:
            return self.radio_range.min_frequency_hz

        if frequency_hz < self.radio_range.min_frequency_hz:
            return self.radio_range.max_frequency_hz

        return frequency_hz
