# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for the trip telemetry runtime."""

from datetime import datetime, timezone

from controllers.automotive import TripStatus
from messaging.contracts.automotive import TRIP_STATE_TOPIC, encode_vehicle_state
from messaging.contracts.automotive.vehicle_state_decoder import decode_vehicle_state
from controllers.automotive import VehicleState
from services.trip.trip_runtime import TripRuntime


class _Subscriber:
    def subscribe(self, topic): pass
    def receive(self): raise RuntimeError
    def close(self): pass


class _Publisher:
    def __init__(self): self.messages = []
    def publish(self, topic, payload): self.messages.append((topic, payload))


def test_vehicle_message_advances_and_publishes_trip_state() -> None:
    publisher = _Publisher()
    runtime = TripRuntime(_Subscriber(), publisher)

    message = decode_vehicle_state(encode_vehicle_state(
        VehicleState(
            timestamp=datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc),
            vehicle_speed_m_s=10.0,
        ),
        source="test",
    ))
    runtime._handle_vehicle(message)

    assert publisher.messages[-1][0] == TRIP_STATE_TOPIC
    assert publisher.messages[-1][1]["data"]["status"] == TripStatus.ACTIVE.value
