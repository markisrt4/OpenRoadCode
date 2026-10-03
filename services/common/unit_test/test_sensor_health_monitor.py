# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Sensor stream validity, freshness, independent sources, and receiver lifecycle."""

import threading
import unittest
from unittest.mock import Mock

from services.common.sensor_health_monitor import SensorHealthMonitor

TOPIC = "openroad.navigation.position"


def position(seconds=100, source="gps", cached=False, fix=3):
    return {
        "version": 1, "timestamp": {"seconds": seconds, "nanoseconds": 0}, "source": source,
        "data": {"latitude_rad": 0.1, "longitude_rad": 0.2, "altitude_m": 100,
                 "fix_mode": fix, "satellites_visible": 10, "satellites_used": 8,
                 "accuracy_m": 3, "is_cached": cached},
    }


class SensorHealthMonitorTest(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.monitor = SensorHealthMonitor(monotonic=lambda: self.now)

    def row(self, source="gps"):
        return next(row for row in self.monitor.snapshots() if row.topic == TOPIC and row.source == source)

    def test_unseen_streams_are_unknown_not_failed(self):
        self.assertEqual(len(self.monitor.snapshots()), 6)
        self.assertTrue(all(row.state == "not_observed" for row in self.monitor.snapshots()))

    def test_freshness_and_rate_use_monotonic_receipt_times(self):
        self.monitor.observe(TOPIC, position())
        self.now = 1
        self.monitor.observe(TOPIC, position(101))
        row = self.row()
        self.assertEqual(row.state, "streaming")
        self.assertEqual(row.message_rate_hz, 1)
        self.now = 12
        row = self.row()
        self.assertEqual(row.state, "stale")
        self.assertEqual(row.message_rate_hz, 0)
        self.assertEqual(row.last_received_age_seconds, 11)

    def test_repeated_timestamp_does_not_keep_a_frozen_sample_healthy(self):
        self.monitor.observe(TOPIC, position())
        self.now = 11
        self.monitor.observe(TOPIC, position())
        row = self.row()
        self.assertEqual(row.last_received_age_seconds, 0)
        self.assertEqual(row.last_sample_age_seconds, 11)
        self.assertEqual(row.state, "stale")
        self.monitor.observe(TOPIC, position(101))
        self.assertEqual(self.row().state, "streaming")

    def test_cached_or_no_fix_position_is_degraded_not_streaming(self):
        self.monitor.observe(TOPIC, position(cached=True))
        self.assertEqual(self.row().state, "degraded")
        self.monitor.observe(TOPIC, position(101, fix=1))
        self.assertIn("No valid GPS fix", self.row().detail)

    def test_invalid_messages_do_not_advance_valid_sample_age(self):
        self.monitor.observe(TOPIC, position())
        self.now = 2
        invalid = position(102)
        invalid["data"]["latitude_rad"] = float("nan")
        self.monitor.observe(TOPIC, invalid)
        self.assertEqual(self.row().state, "invalid")
        self.assertEqual(self.row().invalid_message_count, 1)
        self.assertEqual(self.row().last_sample_age_seconds, 2)
        self.monitor.observe(TOPIC, position(103))
        self.assertEqual(self.row().state, "streaming")
        self.assertEqual(self.row().invalid_message_count, 1)

    def test_an_active_source_does_not_mask_a_stale_source(self):
        self.monitor.observe(TOPIC, position(source="gps-a"))
        self.now = 11
        self.monitor.observe(TOPIC, position(111, source="gps-b"))
        self.assertEqual(self.row("gps-a").state, "stale")
        self.assertEqual(self.row("gps-b").state, "streaming")

    def test_source_cardinality_is_bounded(self):
        for i in range(100):
            self.now = float(i)
            self.monitor.observe(TOPIC, position(i, source=f"gps-{i}"))
        self.assertLessEqual(len(self.monitor._observations), 48)

    def test_other_sensor_contracts_and_nonfinite_magnetic_data(self):
        vectors = {"x": 0.0, "y": 1.0, "z": 2.0}
        samples = {
            "openroad.navigation.imu": {"acceleration_m_s2": vectors, "linear_acceleration_m_s2": vectors, "angular_velocity_rad_s": vectors},
            "openroad.navigation.magnetic_field": {"magnetic_field_ut": vectors},
            "openroad.navigation.attitude": {"heading_rad": 0.0, "pitch_rad": 0.0, "roll_rad": 0.0},
            "openroad.environmental.ambient_light": {"illuminance_lux": 100.0},
            "openroad.environmental.barometric": {"pressure_pa": 100000.0, "temperature_c": 25.0, "altitude_m": 0.0, "relative_altitude_m": 0.0, "vertical_speed_m_s": 0.0},
        }
        for topic, data in samples.items():
            payload = {"version": 1, "source": "test", "timestamp": {"seconds": 100, "nanoseconds": 0}, "data": data}
            if topic.endswith(".imu"):
                payload["frame_id"] = "vehicle"
            self.monitor.observe(topic, payload)
        self.assertEqual(sum(row.state == "streaming" for row in self.monitor.snapshots()), 5)
        magnetic = {"version": 1, "source": "test", "timestamp": {"seconds": 101, "nanoseconds": 0},
                    "data": {"magnetic_field_ut": {"x": float("nan"), "y": 0, "z": 0}}}
        self.monitor.observe("openroad.navigation.magnetic_field", magnetic)
        self.assertEqual(next(row for row in self.monitor.snapshots() if row.name == "Magnetometer").state, "invalid")

    def test_backward_source_clock_is_degraded_and_recovers(self):
        self.monitor.observe(TOPIC, position(100))
        self.now = 1
        self.monitor.observe(TOPIC, position(99))
        self.assertEqual(self.row().state, "degraded")
        self.assertIn("timestamp moved backward", self.row().detail)
        self.monitor.observe(TOPIC, position(101))
        self.assertEqual(self.row().state, "streaming")

    def test_missing_optional_transport_does_not_crash_monitor(self):
        def missing():
            raise ModuleNotFoundError("zmq", name="zmq")
        monitor = SensorHealthMonitor(subscriber_factory=missing)
        monitor.start()
        self.assertIn("pyzmq is missing", monitor.status)
        monitor.close()

    def test_close_unblocks_and_releases_receive_thread(self):
        entered, closed = threading.Event(), threading.Event()
        subscriber = Mock()
        def receive():
            entered.set()
            closed.wait(2)
            raise RuntimeError("closed")
        subscriber.receive.side_effect = receive
        subscriber.close.side_effect = closed.set
        monitor = SensorHealthMonitor(subscriber_factory=lambda: subscriber)
        try:
            monitor.start()
            self.assertTrue(entered.wait(2))
        finally:
            monitor.close()
        self.assertIsNone(monitor._thread)
        self.assertEqual(monitor.status, "stopped")
        self.assertEqual(subscriber.subscribe.call_count, 6)


if __name__ == "__main__":
    unittest.main()
