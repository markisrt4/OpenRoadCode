# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging

from common.logging.structured import current_operation, event, operation

from .radio_backend_if import RadioBackendIf
from .radio_controller_if import RadioControllerIf
from .radio_types import RadioMode, RadioPreset, RadioRange

LOGGER = logging.getLogger("radio.rf")


def _error_fields(error: Exception) -> dict:
    fields = {"exception_type": type(error).__name__}
    code = getattr(error, "code", None)
    if type(code) is int:
        fields["error_code"] = code
    return fields


def format_frequency(frequency_hz: int) -> str:
    """Format a frequency in Hz using a compact human-readable unit."""

    if frequency_hz >= 1_000_000:
        value = f"{frequency_hz / 1_000_000:.3f}".rstrip("0").rstrip(".")
        return f"{value} MHz"

    if frequency_hz >= 1_000:
        value = f"{frequency_hz / 1_000:.3f}".rstrip("0").rstrip(".")
        return f"{value} kHz"

    return f"{frequency_hz} Hz"


class RadioController(RadioControllerIf):
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
        self._presets = list(presets)
        self.default_mode = default_mode
        self.radio_range = radio_range

        self.current_preset_index = 0
        self.current_mode = default_mode
        self.current_frequency_hz = (
            radio_range.start_frequency_hz
            if radio_range is not None
            else self._presets[0].frequency_hz
        )
        self._started = False
        self._frequency_available: bool | None = None

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def is_available(self) -> bool:
        return True

    @property
    def status_message(self) -> str | None:
        return None

    @property
    def presets(self) -> list[RadioPreset]:
        return self._presets

    def start(self) -> int:
        """Start the backend and tune the configured initial frequency."""
        if self._started:
            return self.current_frequency_hz
        with operation(current_operation()):
            event(
                LOGGER, logging.INFO, "receiver.start_requested", "Radio receiver start requested"
            )
            try:
                self.backend.start()
                try:
                    self.set_mode(self.default_mode)
                    if self.radio_range is not None:
                        self.current_frequency_hz = self.radio_range.start_frequency_hz
                    frequency_hz = self.set_frequency(self.current_frequency_hz)
                except Exception:
                    self.backend.stop()
                    raise
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "receiver.start_failed",
                    "Radio receiver start failed",
                    **_error_fields(error),
                )
                raise
            self._started = True
            event(
                LOGGER,
                logging.INFO,
                "receiver.started",
                "Radio receiver started",
                frequency_hz=frequency_hz,
                mode=self.current_mode.name,
            )
            return frequency_hz

    def stop(self) -> None:
        """Stop the radio backend."""
        if not self._started:
            return
        with operation(current_operation()):
            try:
                self.backend.stop()
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "receiver.stop_failed",
                    "Radio receiver stop failed",
                    **_error_fields(error),
                )
                raise
            else:
                event(LOGGER, logging.INFO, "receiver.stopped", "Radio receiver stopped")
            finally:
                self._started = False

    def get_frequency(self) -> int:
        """Return the controller's current frequency without transport I/O."""
        return self.current_frequency_hz

    def refresh_frequency(self) -> int:
        """Read the current frequency from the backend and synchronize state."""
        try:
            frequency_hz = self._wrap_frequency(self.backend.get_frequency())
        except Exception as error:
            if self._frequency_available is not False:
                event(
                    LOGGER,
                    logging.WARNING,
                    "frequency.unavailable",
                    "Radio frequency read unavailable",
                    **_error_fields(error),
                )
            self._frequency_available = False
            raise
        if self._frequency_available is False:
            event(LOGGER, logging.INFO, "frequency.recovered", "Radio frequency read recovered")
        self._frequency_available = True
        changed = self.current_frequency_hz != frequency_hz
        self.current_frequency_hz = frequency_hz
        event(
            LOGGER,
            logging.INFO if changed else logging.DEBUG,
            "frequency.changed" if changed else "frequency.refreshed",
            "Radio frequency synchronized",
            frequency_hz=frequency_hz,
        )
        return frequency_hz

    def set_mode(self, mode: RadioMode) -> RadioMode:
        """Set and return the active demodulation mode."""
        with operation(current_operation()):
            try:
                self.backend.set_mode(mode.name, mode.bandwidth)
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "mode.failed",
                    "Radio mode change failed",
                    mode=mode.name,
                    bandwidth_hz=mode.bandwidth,
                    **_error_fields(error),
                )
                raise
            self.current_mode = mode
            event(
                LOGGER,
                logging.INFO,
                "mode.changed",
                "Radio mode set",
                mode=mode.name,
                bandwidth_hz=mode.bandwidth,
            )
            return mode

    def tune_preset(self, preset: RadioPreset) -> RadioPreset:
        """Tune and return a preset."""
        with operation(current_operation()):
            self.set_mode(preset.mode)
            self.set_frequency(preset.frequency_hz)
            try:
                self.current_preset_index = self._presets.index(preset)
            except ValueError:
                pass
            event(
                LOGGER,
                logging.INFO,
                "preset.selected",
                "Radio preset selected",
                frequency_hz=self.current_frequency_hz,
                mode=self.current_mode.name,
            )
            return preset

    def tune_preset_index(self, index: int) -> RadioPreset:
        """Tune a preset by zero-based index, wrapping at either end."""
        if not self._presets:
            raise ValueError("No radio presets configured")

        wrapped_index = index % len(self._presets)
        self.current_preset_index = wrapped_index
        return self.tune_preset(self._presets[wrapped_index])

    def next_preset(self) -> RadioPreset:
        """Tune and return the next configured preset."""
        return self.tune_preset_index(self.current_preset_index + 1)

    def previous_preset(self) -> RadioPreset:
        """Tune and return the previous configured preset."""
        return self.tune_preset_index(self.current_preset_index - 1)

    def next_station(self) -> RadioPreset:
        """Compatibility alias used by existing radio panels and adapters."""
        return self.next_preset()

    def previous_station(self) -> RadioPreset:
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
        with operation(current_operation()):
            try:
                self.backend.set_frequency(wrapped_frequency_hz)
            except Exception as error:
                event(
                    LOGGER,
                    logging.ERROR,
                    "frequency.failed",
                    "Radio tuning failed",
                    frequency_hz=wrapped_frequency_hz,
                    **_error_fields(error),
                )
                raise
            self.current_frequency_hz = wrapped_frequency_hz
            event(
                LOGGER,
                logging.INFO,
                "frequency.tuned",
                "Radio frequency tuned",
                frequency_hz=wrapped_frequency_hz,
            )
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
