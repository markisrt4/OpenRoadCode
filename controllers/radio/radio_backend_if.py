from abc import ABC, abstractmethod
class RadioBackendIf(ABC):
    """Hardware-independent contract for controlling a radio receiver."""

    @abstractmethod
    def start(self) -> object:
        """Start the receiver backend."""

    @abstractmethod
    def stop(self) -> object:
        """Stop the receiver backend."""

    @abstractmethod
    def get_frequency(self) -> int:
        """Return the current tuned frequency.

        @return Tuned frequency in hertz.
        """

    @abstractmethod
    def set_frequency(self, frequency_hz: int) -> object:
        """Tune to a frequency.

        @param frequency_hz Target frequency in hertz.
        """

    @abstractmethod
    def set_mode(self, mode: str, bandwidth: int) -> object:
        """Set the receiver demodulation mode.

        @param mode Backend demodulation mode name.
        @param bandwidth Receiver bandwidth in hertz.
        """

    @abstractmethod
    def get_signal_strength(self) -> float | str | None:
        """Return receiver signal strength.

        @return Signal strength in dBFS, or ``None`` when unavailable.
        """

    @abstractmethod
    def get_snr(self) -> float | str | None:
        """Return the signal-to-noise ratio.

        @return Ratio in decibels, or ``None`` when unavailable.
        """

    @abstractmethod
    def get_rds(self) -> str | None:
        """Return decoded Radio Data System text.

        @return RDS text, or ``None`` when unavailable.
        """
