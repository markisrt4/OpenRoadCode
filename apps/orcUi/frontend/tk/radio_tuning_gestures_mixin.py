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
        if tuning_range is None:
            return
        low, high, step = tuning_range
        if mode in ("WFM", "FM") and 88_000_000 <= frequency <= 108_000_000:
            low, high, step = 88_100_000, 107_900_000, 200_000
        target = next_channel(frequency, direction, low=low, high=high, step=step)
        if target != frequency:
            self._session.request(RadioRequest(
                RadioAction.TUNE_FREQUENCY, frequency_hz=target))

    def _manual_tune(self, direction: int) -> None:
        """US FM buttons move 100 kHz; other profiles retain their own step."""
        state = self._state
        if not state.receiver_running or state.view == "adsb":
            return
        frequency = state.station.frequency_hz
        if not frequency:
            return
        mode = state.station.mode_name.upper()
        if mode not in ("WFM", "FM") or not 88_000_000 <= frequency <= 108_000_000:
            action = RadioAction.TUNE_UP if direction > 0 else RadioAction.TUNE_DOWN
            self._session.request(RadioRequest(action))
            return
        target = max(88_000_000, min(108_000_000, frequency + direction * 100_000))
        if target != frequency:
            self._session.request(RadioRequest(
                RadioAction.TUNE_FREQUENCY, frequency_hz=target))
