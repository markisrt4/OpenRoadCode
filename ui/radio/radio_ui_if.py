"""! @brief Explicit UI contract and display values for radio reception."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from ..ui_if import UiIf
from .playback_request_handler_if import PlaybackRequestHandlerIf
from .preset_request_handler_if import PresetRequestHandlerIf
from .station_request_handler_if import StationRequestHandlerIf
from .tuning_request_handler_if import TuningRequestHandlerIf


class ModulationType(Enum):
    """! @brief Demodulation types supported by the radio UI."""

    AM = auto()
    FM = auto()
    NFM = auto()
    WFM = auto()


@dataclass(frozen=True, slots=True)
class RadioMode:
    """! @brief Describe a UI-visible demodulation mode.

    @param modulation Demodulation type displayed by the UI.
    @param bandwidth_hz Receiver bandwidth in hertz.
    @param step_hz Tuning increment in hertz.
    """

    modulation: ModulationType
    bandwidth_hz: int
    step_hz: int


@dataclass(frozen=True, slots=True)
class RadioPreset:
    """! @brief Describe one application radio preset.

    The fields mirror the existing application preset design.

    @param label User-visible preset name.
    @param frequency_hz Preset frequency in hertz.
    @param mode Preset demodulation mode and tuning configuration.
    """

    label: str
    frequency_hz: int
    mode: RadioMode


@dataclass(frozen=True, slots=True)
class TunedSignal:
    """! @brief Represent the currently tuned signal.

    Signal strength uses dBFS to match the current SDR backend. Optional fields
    are ``None`` when the receiver or decoder cannot provide them.

    @param frequency_hz Current tuned frequency in hertz.
    @param mode Current demodulation mode and tuning configuration.
    @param snr_db Signal-to-noise ratio in decibels, or None when unavailable.
    @param signal_strength_dbfs Signal strength in dBFS, or None when unavailable.
    @param call_sign Station call sign, or None when unavailable.
    @param station_name Human-readable station name, or None when unavailable.
    @param rds_text Decoded Radio Data System text, or None when unavailable.
    """

    frequency_hz: int
    mode: RadioMode
    snr_db: float | None = None
    signal_strength_dbfs: float | None = None
    call_sign: str | None = None
    station_name: str | None = None
    rds_text: str | None = None


class RadioUiIf(UiIf, ABC):
    """! @brief Display radio telemetry, controls, and presets.

    ``None`` passed to :meth:`set_signal` means the receiver has no currently
    available tuning state. Presets appear in the order they are added.
    """

    @abstractmethod
    def set_signal(self, signal: TunedSignal | None) -> None:
        """! @brief Set the tuned-signal display state.

        @param signal Current tuned signal, or None when unavailable.
        """
        ...

    @abstractmethod
    def add_preset(self, preset: RadioPreset) -> None:
        """! @brief Add one preset to the radio UI.

        @param preset Preset to add.
        """
        ...

    @abstractmethod
    def set_preset_request_handler(
        self,
        handler: PresetRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the preset request handler.

        @param handler Preset request handler, or None to disconnect it.
        """
        ...

    @abstractmethod
    def set_playback_request_handler(
        self,
        handler: PlaybackRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the playback request handler.

        @param handler Playback request handler, or None to disconnect it.
        """
        ...

    @abstractmethod
    def set_station_request_handler(
        self,
        handler: StationRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the station-navigation request handler.

        @param handler Station request handler, or None to disconnect it.
        """
        ...

    @abstractmethod
    def set_tuning_request_handler(
        self,
        handler: TuningRequestHandlerIf | None,
    ) -> None:
        """! @brief Set or clear the frequency-tuning request handler.

        @param handler Tuning request handler, or None to disconnect it.
        """
        ...
