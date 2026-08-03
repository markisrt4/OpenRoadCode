"""Concrete no-op radio UI implementation."""

from ui.radio.playback_request_handler_if import PlaybackRequestHandlerIf
from ui.radio.preset_request_handler_if import PresetRequestHandlerIf
from ui.radio.radio_ui_if import RadioPreset, RadioUiIf, TunedSignal
from ui.radio.station_request_handler_if import StationRequestHandlerIf
from ui.radio.tuning_request_handler_if import TuningRequestHandlerIf
from ui.ui_stub import UiStub


class RadioUiStub(UiStub, RadioUiIf):
    """Ignore radio display updates and callback registration."""

    def set_signal(self, signal: TunedSignal | None) -> None:
        pass

    def add_preset(self, preset: RadioPreset) -> None:
        pass

    def set_preset_request_handler(
        self,
        handler: PresetRequestHandlerIf | None,
    ) -> None:
        pass

    def set_playback_request_handler(
        self,
        handler: PlaybackRequestHandlerIf | None,
    ) -> None:
        pass

    def set_station_request_handler(
        self,
        handler: StationRequestHandlerIf | None,
    ) -> None:
        pass

    def set_tuning_request_handler(
        self,
        handler: TuningRequestHandlerIf | None,
    ) -> None:
        pass
