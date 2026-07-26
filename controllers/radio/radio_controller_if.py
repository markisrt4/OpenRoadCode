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
        """Return whether the receiver backend is started."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether radio control is configured and available."""

    @property
    @abstractmethod
    def status_message(self) -> str | None:
        """Return an availability message, if one applies."""

    @property
    @abstractmethod
    def presets(self) -> Sequence[RadioPreset]:
        """Return configured radio presets."""

    @abstractmethod
    def start(self) -> int:
        """Start the receiver and return its initial frequency."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the receiver."""

    @abstractmethod
    def get_frequency(self) -> int:
        """Return the controller's current frequency in hertz."""

    @abstractmethod
    def refresh_frequency(self) -> int:
        """Refresh the current frequency from the receiver backend."""

    @abstractmethod
    def set_mode(self, mode: RadioMode) -> RadioMode:
        """Set and return the active demodulation mode."""

    @abstractmethod
    def tune_preset(self, preset: RadioPreset) -> RadioPreset:
        """Tune and return a preset."""

    @abstractmethod
    def tune_preset_index(self, index: int) -> RadioPreset:
        """Tune a configured preset by wrapping index."""

    @abstractmethod
    def next_preset(self) -> RadioPreset:
        """Tune and return the next preset."""

    @abstractmethod
    def previous_preset(self) -> RadioPreset:
        """Tune and return the previous preset."""

    @abstractmethod
    def next_station(self) -> RadioPreset:
        """Compatibility name for tuning the next preset."""

    @abstractmethod
    def previous_station(self) -> RadioPreset:
        """Compatibility name for tuning the previous preset."""

    @abstractmethod
    def frequency_up(self, delta_hz: int | None = None) -> int:
        """Increase frequency by an explicit or mode-defined step."""

    @abstractmethod
    def frequency_down(self, delta_hz: int | None = None) -> int:
        """Decrease frequency by an explicit or mode-defined step."""

    @abstractmethod
    def set_frequency(self, frequency_hz: int) -> int:
        """Tune and return a validated frequency in hertz."""

    @abstractmethod
    def get_signal_strength(self) -> float | str | None:
        """Return receiver signal strength when available."""

    @abstractmethod
    def get_snr(self) -> float | str | None:
        """Return receiver signal-to-noise ratio when available."""

    @abstractmethod
    def get_rds(self) -> str | None:
        """Return decoded Radio Data System text when available."""
