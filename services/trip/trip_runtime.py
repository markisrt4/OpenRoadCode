# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Derive and publish automotive trip state from public telemetry topics."""

from __future__ import annotations

import math
from datetime import timedelta
from threading import Lock

from controllers.automotive import TripIf, TripTracker, VehicleState
from controllers.navigation.navigation_state import GroundMotionState, PositionState
from messaging.contracts.automotive import (
    VEHICLE_STATE_TOPIC,
    TripStatePublisher,
    VehicleStateMessage,
    decode_vehicle_state,
)
from messaging.contracts.common.timestamp import UNIX_EPOCH
from messaging.contracts.navigation import (
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    MotionStateMessage,
    PositionStateMessage,
    decode_motion_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.subscriber_if import SubscriberIf


def _datetime(timestamp):
    return UNIX_EPOCH + timedelta(
        seconds=timestamp.seconds,
        microseconds=timestamp.nanoseconds / 1000.0,
    )


class TripRuntime:
    """Consume public vehicle/navigation telemetry and publish derived trip state."""

    def __init__(
        self,
        subscriber: SubscriberIf,
        publisher,
        *,
        tracker: TripIf | None = None,
        publish_source: str = "trip-service",
    ) -> None:
        self._tracker = tracker or TripTracker()
        self._publisher = TripStatePublisher(publisher, source=publish_source)
        self._lock = Lock()
        self._dispatcher = MessageDispatcher(subscriber, max_workers=1)
        self._dispatcher.register(VEHICLE_STATE_TOPIC, decode_vehicle_state, self._handle_vehicle)
        self._dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, self._handle_position)
        self._dispatcher.register(MOTION_STATE_TOPIC, decode_motion_state, self._handle_motion)

    def start(self) -> None:
        """Start consuming telemetry."""
        self._dispatcher.start()

    def close(self) -> None:
        """Stop consuming telemetry."""
        self._dispatcher.close()

    def _publish_after(self, observation) -> None:
        with self._lock:
            observation()
            self._publisher.publish(self._tracker.snapshot())

    def _handle_vehicle(self, message: VehicleStateMessage) -> None:
        data = message.data
        state = VehicleState(
            timestamp=_datetime(message.timestamp),
            engine_speed_rad_s=data.engine_speed_rad_s,
            vehicle_speed_m_s=data.vehicle_speed_m_s,
            transmission_gear=data.transmission_gear,
            throttle_position=data.throttle_position,
            accelerator_pedal_position=data.accelerator_pedal_position,
            engine_load=data.engine_load,
            intake_manifold_pressure_pa=data.intake_manifold_pressure_pa,
            barometric_pressure_pa=data.barometric_pressure_pa,
            boost_pressure_pa=data.boost_pressure_pa,
            mass_air_flow_kg_s=data.mass_air_flow_kg_s,
            coolant_temperature_k=data.coolant_temperature_k,
            intake_air_temperature_k=data.intake_air_temperature_k,
            fuel_level=data.fuel_level,
            commanded_equivalence_ratio=data.commanded_equivalence_ratio,
            engine_fuel_rate_m3_s=data.engine_fuel_rate_m3_s,
            control_voltage_v=data.control_voltage_v,
        )
        self._publish_after(lambda: self._tracker.observe_vehicle_state(state))

    def _handle_position(self, message: PositionStateMessage) -> None:
        data = message.data
        state = PositionState(
            received_at=_datetime(message.timestamp),
            latitude_deg=None if data.latitude_rad is None else math.degrees(data.latitude_rad),
            longitude_deg=None if data.longitude_rad is None else math.degrees(data.longitude_rad),
            altitude_m=data.altitude_m,
            fix_mode=data.fix_mode,
            satellites_visible=data.satellites_visible,
            satellites_used=data.satellites_used,
            accuracy_m=data.accuracy_m,
            source=message.source,
            is_cached=data.is_cached,
        )
        self._publish_after(lambda: self._tracker.observe_position_state(state))

    def _handle_motion(self, message: MotionStateMessage) -> None:
        data = message.data
        state = GroundMotionState(
            received_at=_datetime(message.timestamp),
            speed_mps=data.ground_speed_m_s,
            course_deg=None if data.course_rad is None else math.degrees(data.course_rad),
            source=message.source,
        )
        self._publish_after(lambda: self._tracker.observe_ground_motion_state(state))
