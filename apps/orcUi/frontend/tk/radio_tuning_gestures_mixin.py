# SPDX-License-Identifier: MIT
"""Profile-aware tuning gestures for the native radio panel."""

from ui.radio.rf_radio_if import RadioAction, RadioRequest


def next_channel(frequency_hz: int, direction: int, *, low: int, high: int,
                 step: int) -> int:
    """Move to the next channel center, even from an off-grid frequency."""
    if step <= 0 or direction == 0:
        return frequency_hz
    if direction > 0:
        candidate = low + ((frequency_hz - low) // step + 1) * step
    else:
        candidate = low + ((frequency_hz - low - 1) // step) * step
    return max(low, min(high, candidate))


class RadioTuningGesturesMixin:
    """Keep receiver input routing separate from Tk widget construction."""

    def _gesture_tune(self, direction: int) -> None:
        state = self._state
        if not state.receiver_running or state.view == "adsb" or not direction:
            return
        frequency = state.station.frequency_hz
        if not frequency:
            return
        mode = state.station.mode_name.upper()
        tuning_range = state.tuning_range
        if mode in ("WFM", "FM") and 88_000_000 <= frequency <= 108_000_000:
            low, high, step = 88_100_000, 107_900_000, 200_000
        elif tuning_range is not None:
            low, high, step = tuning_range
        else:
            return
        target = next_channel(frequency, direction, low=low, high=high, step=step)
        if target != frequency:
            self._session.request(RadioRequest(
                RadioAction.TUNE_FREQUENCY, frequency_hz=target))

    def _manual_tune(self, direction: int) -> None:
        """Use broadcast channel spacing for FM and profile steps otherwise."""
        state = self._state
        if not state.receiver_running or state.view == "adsb" or not direction:
            return
        if (state.station.mode_name.upper() in ("FM", "WFM")
                and 88_000_000 <= state.station.frequency_hz <= 108_000_000):
            self._gesture_tune(direction)
        else:
            action = RadioAction.TUNE_UP if direction > 0 else RadioAction.TUNE_DOWN
            self._session.request(RadioRequest(action))

    def _previous_preset(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        self._session.request(RadioRequest(RadioAction.PREVIOUS))

    def _next_preset(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        self._session.request(RadioRequest(RadioAction.NEXT))

    def _recenter_spectrum(self) -> None:
        if self._state.receiver_running and self._state.view != "adsb":
            self._session.request(RadioRequest(RadioAction.RECENTER))

    def _tune_spectrum_frequency(self, frequency_hz: int) -> None:
        if self._state.receiver_running and self._state.view != "adsb":
            self._session.request(RadioRequest(
                RadioAction.TUNE_FREQUENCY, frequency_hz=frequency_hz))

    def _tune_down(self) -> None:
        if self._sdrforge_view is not None:
            self._manual_tune(-1)
            return
        self._session.request(RadioRequest(RadioAction.TUNE_DOWN))

    def _tune_up(self) -> None:
        if self._sdrforge_view is not None:
            self._manual_tune(1)
            return
        self._session.request(RadioRequest(RadioAction.TUNE_UP))
