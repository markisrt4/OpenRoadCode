# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import pytest

from controllers.automotive import AutomotiveTelemetryProfile
from messaging.contracts.automotive import (
    decode_automotive_telemetry_profile_request,
    encode_automotive_telemetry_profile_request,
)


def test_telemetry_profile_request_round_trip() -> None:
    payload = encode_automotive_telemetry_profile_request(
        AutomotiveTelemetryProfile.ECU,
        source="orc-ui",
    )
    request = decode_automotive_telemetry_profile_request(payload)

    assert request.profile is AutomotiveTelemetryProfile.ECU
    assert request.source == "orc-ui"


def test_telemetry_profile_request_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError):
        decode_automotive_telemetry_profile_request(
            {"version": 1, "source": "test", "profile": "warp-drive"}
        )
