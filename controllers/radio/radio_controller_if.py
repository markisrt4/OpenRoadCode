"""Public interface for radio controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .radio_types import RadioMode, RadioPreset


class RadioControllerIf(ABC):
    """Control radio tuning, presets, modes, and receiver telemetry."""

    @property
    @abstractmethod
    def is_started(self) -> bool:
        """Return whether the receiver backend is started.

        @retval True The receiver backend is started.
        @retval False The receiver backend is stopped.
        """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether radio control is configured and available.

        @retval True Radio control is available.
        @retval False Radio control is unavailable.
        """

    @property
    @abstractmethod
    def status_message(self) -> str | None:
        """Return an availability message, if one applies.

        @return Human-readable status, or ``None`` when no message applies.
        """

    @property
    @abstractmethod
    def presets(self) -> Sequence[RadioPreset]:
        """Return configured radio presets.

        @return Ordered configured radio presets.
        """

    @abstractmethod
    def start(self) -> int:
        """Start the receiver and return its initial frequency.

        @return Initial tuned frequency in hertz.
        """

    @abstractmethod
    def stop(self) -> None:
        """Stop the receiver."""

    @abstractmethod
    def get_frequency(self) -> int:
        """Return the controller's current frequency in hertz.

        @return Current tuned frequency in hertz.
        """

    @abstractmethod
    def refresh_frequency(self) -> int:
        """Refresh the current frequency from the receiver backend.

        @return Refreshed tuned frequency in hertz.
        """

    @abstractmethod
    def set_mode(self, mode: RadioMode) -> RadioMode:
        """Set and return the active demodulation mode.

        @param mode Demodulation mode to activate.
        @return Active demodulation mode.
        """

    @abstractmethod
    def tune_preset(self, preset: RadioPreset) -> RadioPreset:
        """Tune and return a preset.

        @param preset Preset to tune.
        @return Tuned preset.
        """

    @abstractmethod
    def tune_preset_index(self, index: int) -> RadioPreset:
        """Tune a configured preset by wrapping index.

        @param index Preset index, wrapped into the configured preset list.
        @return Tuned preset.
        """

    @abstractmethod
    def next_preset(self) -> RadioPreset:
        """Tune and return the next preset.

        @return Newly tuned preset.
        """

    @abstractmethod
    def previous_preset(self) -> RadioPreset:
        """Tune and return the previous preset.

        @return Newly tuned preset.
        """

    @abstractmethod
    def next_station(self) -> RadioPreset:
        """Compatibility name for tuning the next preset.

        @return Newly tuned preset.
        """

    @abstractmethod
    def previous_station(self) -> RadioPreset:
        """Compatibility name for tuning the previous preset.

        @return Newly tuned preset.
        """

    @abstractmethod
    def frequency_up(self, delta_hz: int | None = None) -> int:
        """Increase frequency by an explicit or mode-defined step.

        @param delta_hz Explicit positive step in hertz, or ``None`` to use
            the active mode's configured step.
        @return Resulting tuned frequency in hertz.
        """

    @abstractmethod
    def frequency_down(self, delta_hz: int | None = None) -> int:
        """Decrease frequency by an explicit or mode-defined step.

        @param delta_hz Explicit positive step in hertz, or ``None`` to use
            the active mode's configured step.
        @return Resulting tuned frequency in hertz.
        """

    @abstractmethod
    def set_frequency(self, frequency_hz: int) -> int:
        """Tune and return a validated frequency in hertz.

        @param frequency_hz Target frequency in hertz.
        @return Validated tuned frequency in hertz.
        """

    @abstractmethod
    def get_signal_strength(self) -> float | str | None:
        """Return receiver signal strength when available.

        @return Signal strength reported by the backend, or ``None`` when
            unavailable.
        """

    @abstractmethod
    def get_snr(self) -> float | str | None:
        """Return receiver signal-to-noise ratio when available.

        @return Signal-to-noise ratio reported by the backend, or ``None``
            when unavailable.
        """

    @abstractmethod
    def get_rds(self) -> str | None:
        """Return decoded Radio Data System text when available.

        @return Decoded RDS text, or ``None`` when unavailable.
        """
