# SPDX-License-Identifier: MIT
"""Hardware-free requested-versus-observed receiver mode checks."""

from dataclasses import replace

from ui.radio.radio_profile_state import RadioProfileState
from ui.radio.rf_radio_if import (
    RadioTelemetry, RfRadioState, receiver_mode_mismatch,
)


def state(expected: str = "NFM", actual: str | None = "WFM",
          *, tuned: int = 162_550_000, observed: int = 162_550_000,
          running: bool | None = True) -> RfRadioState:
    return RfRadioState(
        station=RadioProfileState("NOAA", tuned, expected, "weather", "Weather"),
        profiles=(),
        telemetry=RadioTelemetry(
            frequency_hz=observed, mode=actual,
            bandwidth_hz=200_000 if actual == "WFM" else 12_500,
            receiver_running=running,
        ),
    )


def test_mismatch_is_reported_for_same_station_and_running_receiver() -> None:
    assert receiver_mode_mismatch(state())


def test_matching_mode_is_not_mismatch() -> None:
    assert not receiver_mode_mismatch(state(actual="NFM"))


def test_fm_alias_matches_wfm() -> None:
    assert not receiver_mode_mismatch(state(expected="FM", actual="WFM"))


def test_stale_frequency_does_not_trigger_mismatch() -> None:
    assert not receiver_mode_mismatch(state(observed=104_300_000))


def test_missing_or_stopped_receiver_does_not_trigger_mismatch() -> None:
    assert not receiver_mode_mismatch(state(actual=None))
    assert not receiver_mode_mismatch(state(running=False))
    assert not receiver_mode_mismatch(state(running=None))
