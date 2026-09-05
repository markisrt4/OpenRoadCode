# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared ORCui camera runtime for native map panels."""

from __future__ import annotations

import math

from controllers.map_renderer.flight_camera_controller import FlightCameraController, FlightState
from controllers.map_renderer.map_request_handler import MapRequestHandler
from messaging.contracts.navigation import (
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    MotionStateMessage,
    PositionStateMessage,
    decode_motion_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT
from protocols.map_renderer.map_renderer_client import MapRendererClient
from ui.navigation import GeoPoint, MapRequestHandlerIf

_MIN_COURSE_UP_SPEED_M_S = 1.5
_MIN_COURSE_POSITION_DELTA_M = 4.0
_DEFAULT_FLIGHT_SPEED_M_S = 30.0
_EARTH_RADIUS_M = 6_378_137.0


class MapCameraRuntime:
    """Feed navigation position and motion into the native map camera."""

    def __init__(
        self,
        *,
        zoom_level: float = 16.5,
        pitch_rad: float = 0.0,
        follow_enabled: bool = True,
    ) -> None:
        self._renderer_client = MapRendererClient()
        self._handler = MapRequestHandler(
            self._renderer_client,
            center=GeoPoint(latitude_rad=0.0, longitude_rad=0.0),
            zoom_level=zoom_level,
            pitch_rad=pitch_rad,
            follow_enabled=follow_enabled,
        )
        self._dispatcher = MessageDispatcher(ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT))
        self._dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, self._on_position_message)
        self._dispatcher.register(MOTION_STATE_TOPIC, decode_motion_state, self._on_motion_message)
        self._course_reference: GeoPoint | None = None
        self._last_position: GeoPoint | None = None
        self._last_heading_rad: float | None = None
        self._last_speed_m_s: float | None = None
        self._flight_controller: FlightCameraController | None = None
        self._closed = False

    @property
    def request_handler(self) -> MapRequestHandlerIf:
        return self._handler

    @property
    def flight_enabled(self) -> bool:
        return self._flight_controller is not None and self._flight_controller.is_running

    def start(self) -> None:
        self._dispatcher.start()

    def start_flight(self) -> bool:
        if self.flight_enabled:
            return True
        point = self._last_position
        if point is None:
            return False
        speed = max(_DEFAULT_FLIGHT_SPEED_M_S, self._last_speed_m_s or 0.0)
        heading_deg = math.degrees(self._last_heading_rad or 0.0)
        self._flight_controller = FlightCameraController(
            self._renderer_client,
            FlightState(
                latitude_deg=math.degrees(point.latitude_rad),
                longitude_deg=math.degrees(point.longitude_rad),
                heading_deg=heading_deg,
                speed_mps=speed,
                zoom=14.0,
                pitch_deg=58.0,
            ),
        )
        self._flight_controller.start()
        return True

    def stop_flight(self) -> None:
        controller = self._flight_controller
        self._flight_controller = None
        if controller is not None:
            controller.stop()

    def adjust_flight(
        self,
        *,
        speed_delta_mps: float = 0.0,
        heading_delta_deg: float = 0.0,
        pitch_delta_deg: float = 0.0,
        zoom_delta: float = 0.0,
    ) -> None:
        controller = self._flight_controller
        if controller is None:
            return
        controller.adjust(
            speed_delta_mps=speed_delta_mps,
            heading_delta_deg=heading_delta_deg,
            pitch_delta_deg=pitch_delta_deg,
            zoom_delta=zoom_delta,
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.stop_flight()
        self._dispatcher.close()
        self._renderer_client.close()

    def _on_position_message(self, message: PositionStateMessage) -> None:
        data = message.data
        if data.latitude_rad is None or data.longitude_rad is None:
            return
        point = GeoPoint(
            latitude_rad=data.latitude_rad,
            longitude_rad=data.longitude_rad,
            altitude_m=data.altitude_m,
        )
        self._last_position = point

        bearing_rad: float | None = None
        reference = self._course_reference
        if reference is None:
            self._course_reference = point
        else:
            distance_m = self._distance_m(reference, point)
            if distance_m >= _MIN_COURSE_POSITION_DELTA_M:
                bearing_rad = self._bearing_rad(reference, point)
                self._course_reference = point
                self._last_heading_rad = bearing_rad

        if self.flight_enabled:
            return

        self._handler.update_follow_camera(point, bearing_rad)
        self._renderer_client.set_position(
            latitude=math.degrees(data.latitude_rad),
            longitude=math.degrees(data.longitude_rad),
        )

    def _on_motion_message(self, message: MotionStateMessage) -> None:
        data = message.data
        speed_m_s = data.ground_speed_m_s
        if speed_m_s is not None:
            self._last_speed_m_s = speed_m_s

        bearing_rad = data.course_rad
        if bearing_rad is None:
            bearing_rad = data.heading_rad
        if bearing_rad is not None:
            self._last_heading_rad = bearing_rad

        if self.flight_enabled:
            return
        if speed_m_s is None or speed_m_s < _MIN_COURSE_UP_SPEED_M_S or bearing_rad is None:
            return
        self._handler.update_follow_bearing(bearing_rad)

    @staticmethod
    def _distance_m(start: GeoPoint, end: GeoPoint) -> float:
        d_lat = end.latitude_rad - start.latitude_rad
        d_lon = end.longitude_rad - start.longitude_rad
        sin_lat = math.sin(d_lat / 2.0)
        sin_lon = math.sin(d_lon / 2.0)
        a = sin_lat * sin_lat + math.cos(start.latitude_rad) * math.cos(end.latitude_rad) * sin_lon * sin_lon
        return 2.0 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))

    @staticmethod
    def _bearing_rad(start: GeoPoint, end: GeoPoint) -> float:
        d_lon = end.longitude_rad - start.longitude_rad
        y = math.sin(d_lon) * math.cos(end.latitude_rad)
        x = (
            math.cos(start.latitude_rad) * math.sin(end.latitude_rad)
            - math.sin(start.latitude_rad) * math.cos(end.latitude_rad) * math.cos(d_lon)
        )
        return math.atan2(y, x)
