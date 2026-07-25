from __future__ import annotations

from .radio_backend_if import RadioBackendIf
from .radio_types import RadioMode, RadioPreset, RadioRange


def format_frequency(frequency_hz: int) -> str:
    """Format a frequency in Hz using a compact human-readable unit."""

    if frequency_hz >= 1_000_000:
        value = f"{frequency_hz / 1_000_000:.3f}".rstrip("0").rstrip(".")
        return f"{value} MHz"

    if frequency_hz >= 1_000:
        value = f"{frequency_hz / 1_000:.3f}".rstrip("0").rstrip(".")
        return f"{value} kHz"

    return f"{frequency_hz} Hz"

class RadioController:
    """Coordinate radio tuning, modes, presets, and receiver telemetry."""

    def __init__(
        self,
        backend: RadioBackendIf,
        presets: list[RadioPreset],
        default_mode: RadioMode,
        radio_range: RadioRange | None = None,
    ) -> None:
        if radio_range is None and not presets:
            raise ValueError("a radio range or at least one preset is required")

        self.backend = backend
        self.presets = list(presets)
        self.default_mode = default_mode
        self.radio_range = radio_range

        self.current_preset_index = 0
        self.current_mode = default_mode
        self.current_frequency_hz = (
            radio_range.start_frequency_hz
            if radio_range is not None
            else self.presets[0].frequency_hz
        )

    def start(self) -> int:
        """Start the backend and tune the configured initial frequency."""
        self.backend.start()
        self.set_mode(self.default_mode)

        if self.radio_range is not None:
            self.current_frequency_hz = self.radio_range.start_frequency_hz

        return self.set_frequency(self.current_frequency_hz)

    def stop(self) -> None:
        """Stop the radio backend."""
        self.backend.stop()

    def get_frequency(self) -> int:
        """Return the controller's current frequency in hertz."""
        """Return the controller's current frequency without transport I/O."""
        return self.current_frequency_hz

    def refresh_frequency(self) -> int:
        """Read the current frequency from the backend and synchronize state."""
        frequency_hz = self._wrap_frequency(self.backend.get_frequency())
        self.current_frequency_hz = frequency_hz
        return frequency_hz

    def set_mode(self, mode: RadioMode) -> RadioMode:
        """Set and return the active demodulation mode."""
        self.backend.set_mode(mode.name, mode.bandwidth)
        self.current_mode = mode
        return mode

    def tune_preset(self, preset: RadioPreset) -> RadioPreset:
        """Tune and return a preset."""
        self.set_mode(preset.mode)
        self.set_frequency(preset.frequency_hz)

        try:
            self.current_preset_index = self.presets.index(preset)
        except ValueError:
            pass

        return preset

    def tune_preset_index(self, index: int) -> RadioPreset:
        """Tune a preset by zero-based index, wrapping at either end."""
        if not self.presets:
            raise ValueError("No radio presets configured")

        wrapped_index = index % len(self.presets)
        self.current_preset_index = wrapped_index
        return self.tune_preset(self.presets[wrapped_index])

    def next_preset(self) -> RadioPreset:
        """Tune and return the next configured preset."""
        return self.tune_preset_index(self.current_preset_index + 1)

    def previous_preset(self) -> RadioPreset:
        """Tune and return the previous configured preset."""
        return self.tune_preset_index(self.current_preset_index - 1)

    def next_station(self) -> RadioPreset:
        """Compatibility alias for `next_preset`."""
        """Compatibility alias used by existing radio panels and adapters."""
        return self.next_preset()

    def previous_station(self) -> RadioPreset:
        """Compatibility alias for `previous_preset`."""
        """Compatibility alias used by existing radio panels and adapters."""
        return self.previous_preset()

    def frequency_up(self, delta_hz: int | None = None) -> int:
        """Increase frequency by an explicit delta or the active mode step."""
        step = self._validated_step(delta_hz)
        return self.set_frequency(self.current_frequency_hz + step)

    def frequency_down(self, delta_hz: int | None = None) -> int:
        """Decrease frequency by an explicit delta or the active mode step."""
        step = self._validated_step(delta_hz)
        return self.set_frequency(self.current_frequency_hz - step)

    def set_frequency(self, frequency_hz: int) -> int:
        """Tune a validated frequency and return the resulting hertz value."""
        if frequency_hz <= 0:
            raise ValueError("frequency_hz must be greater than zero")

        wrapped_frequency_hz = self._wrap_frequency(frequency_hz)
        self.backend.set_frequency(wrapped_frequency_hz)
        self.current_frequency_hz = wrapped_frequency_hz
        return wrapped_frequency_hz

    def get_signal_strength(self) -> float | str | None:
        """Return backend signal strength, or ``None`` when unavailable."""
        return self.backend.get_signal_strength()

    def get_snr(self) -> float | str | None:
        """Return backend signal-to-noise ratio, or ``None`` when unavailable."""
        return self.backend.get_snr()

    def get_rds(self) -> str | None:
        """Return decoded RDS text, or ``None`` when unavailable."""
        return self.backend.get_rds()

    def _validated_step(self, delta_hz: int | None) -> int:
        step = self.current_mode.step_hz if delta_hz is None else delta_hz
        if step <= 0:
            raise ValueError("frequency step must be greater than zero")
        return step

    def _wrap_frequency(self, frequency_hz: int) -> int:
        if self.radio_range is None:
            return frequency_hz

        if frequency_hz > self.radio_range.max_frequency_hz:
            return self.radio_range.min_frequency_hz

        if frequency_hz < self.radio_range.min_frequency_hz:
            return self.radio_range.max_frequency_hz

        return frequency_hz
