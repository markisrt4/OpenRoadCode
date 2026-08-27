# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from datetime import datetime, timezone
import math
import unittest

from controllers.automotive.vehicle_state import VehicleState
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, VehicleStatePublisher
from messaging.publisher_if import PublisherIf


class RecordingPublisher(PublisherIf):
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict]] = []

    def publish(self, topic: str, payload) -> None:
        self.messages.append((topic, dict(payload)))


class VehicleStatePublisherTest(unittest.TestCase):
    def test_publishes_vehicle_contract_on_stable_topic(self) -> None:
        transport = RecordingPublisher()
        publisher = VehicleStatePublisher(transport, source="test-source")
        state = VehicleState(
            timestamp=datetime(2026, 8, 21, 17, 27, tzinfo=timezone.utc),
            engine_speed_rad_s=2.0 * math.pi,
        )

        publisher.publish(state)

        self.assertEqual(len(transport.messages), 1)
        topic, payload = transport.messages[0]
        self.assertEqual(topic, VEHICLE_STATE_TOPIC)
        self.assertEqual(topic, "openroad.vehicle.state")
        self.assertEqual(payload["source"], "test-source")
        self.assertAlmostEqual(payload["data"]["engine_speed_rad_s"], 2.0 * math.pi)


if __name__ == "__main__":
    unittest.main()
