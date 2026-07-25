from abc import ABC, abstractmethod
from typing import Optional

from .radio_types import RadioMode


class RadioBackendIf(ABC):
    """Hardware-independent contract for controlling a radio receiver."""

    @abstractmethod
    def get_frequency(self) -> int:
        """Return the current tuned frequency.

        @return Tuned frequency in hertz.
        """

    @abstractmethod
    def set_frequency(self, frequency_hz: int) -> None:
        """Tune to a frequency.

        @param frequency_hz Target frequency in hertz.
        """

    @abstractmethod
    def set_mode(self, mode: RadioMode) -> None:
        """Set the receiver demodulation mode.

        @param mode Demodulation mode and tuning-step definition.
        """

    @abstractmethod
    def get_signal_strength(self) -> Optional[float]:
        """Return receiver signal strength.

        @return Signal strength in dBFS, or ``None`` when unavailable.
        """

    @abstractmethod
    def get_snr(self) -> Optional[float]:
        """Return the signal-to-noise ratio.

        @return Ratio in decibels, or ``None`` when unavailable.
        """

    @abstractmethod
    def get_rds(self) -> Optional[str]:
        """Return decoded Radio Data System text.

        @return RDS text, or ``None`` when unavailable.
        """
