# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for the ambient light messaging contract."""

from __future__ import annotations

import pytest

from messaging.contracts.environmental import decode_ambient_light_state, encode_ambient_light_state

_TIMESTAMP = {"seconds": 1_700_000_000, "nanoseconds": 123_000_000}


def test_ambient_light_state_round_trip() -> None:
    payload = encode_ambient_light_state(
        timestamp=_TIMESTAMP,
        source="android",
        illuminance_lux=42.5,
    )

    message = decode_ambient_light_state(payload)

    assert message.version == 1
    assert message.timestamp.seconds == _TIMESTAMP["seconds"]
    assert message.timestamp.nanoseconds == _TIMESTAMP["nanoseconds"]
    assert message.source == "android"
    assert message.data.illuminance_lux == 42.5


def test_zero_lux_is_valid() -> None:
    payload = encode_ambient_light_state(
        timestamp=_TIMESTAMP,
        source="android",
        illuminance_lux=0.0,
    )

    assert payload["data"]["illuminance_lux"] == 0.0


@pytest.mark.parametrize("illuminance_lux", (-0.1, float("nan"), float("inf")))
def test_invalid_illuminance_is_rejected(illuminance_lux: float) -> None:
    with pytest.raises(ValueError):
        encode_ambient_light_state(
            timestamp=_TIMESTAMP,
            source="android",
            illuminance_lux=illuminance_lux,
        )
