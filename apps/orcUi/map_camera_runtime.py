# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared ORCui camera runtime for native map panels."""

from __future__ import annotations

import math

from controllers.map_renderer.map_request_handler import MapRequestHandler
from messaging.contracts.navigation import (
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    MotionStateMessage,
    PositionStateMessage,
    decode_motion_state,
    decode_position_state,
)
from messaging.contracts.route_guidance import (
    ROUTE_GUIDANCE_STATE_TOPIC,
    RouteGuidanceStateMessage,
    decode_route_guidance_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT
from protocols.map_renderer.map_renderer_client import MapRendererClient
from ui.navigation import GeoPoint, MapRequestHandlerIf

_MIN_COURSE_UP_SPEED_M_S = 1.5
_MIN_COURSE_POSITION_DELTA_M = 4.0
_EARTH_RADIUS_M = 6_378_137.0


class MapCameraRuntime:
    """Feed public navigation state into ORC map renderers."""

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
        self._dispatcher.register(
            ROUTE_GUIDANCE_STATE_TOPIC,
            decode_route_guidance_state,
            self._on_route_guidance_message,
        )
        self._course_reference: GeoPoint | None = None
        self._latest_position: GeoPoint | None = None
        self._latest_ground_speed_m_s: float | None = None
        self._latest_course_rad: float | None = None
        self._latest_heading_rad: float | None = None
        self._latest_instruction: str | None = None
        self._latest_distance_to_maneuver_m: float | None = None
        self._latest_distance_remaining_m: float | None = None
        self._latest_off_route = False
        self._latest_route_complete = False
        self._closed = False

    @property
    def request_handler(self) -> MapRequestHandlerIf:
        return self._handler

    @property
    def latest_position(self) -> GeoPoint | None:
        return self._latest_position

    @property
    def latest_ground_speed_m_s(self) -> float | None:
        return self._latest_ground_speed_m_s

    @property
    def latest_course_rad(self) -> float | None:
        return self._latest_course_rad

    @property
    def latest_heading_rad(self) -> float | None:
        return self._latest_heading_rad

    @property
    def latest_track_rad(self) -> float | None:
        return self._latest_course_rad if self._latest_course_rad is not None else self._latest_heading_rad

    @property
    def latest_instruction(self) -> str | None:
        return self._latest_instruction

    @property
    def latest_distance_to_maneuver_m(self) -> float | None:
        return self._latest_distance_to_maneuver_m

    @property
    def latest_distance_remaining_m(self) -> float | None:
        return self._latest_distance_remaining_m

    @property
    def latest_off_route(self) -> bool:
        return self._latest_off_route

    @property
    def latest_route_complete(self) -> bool:
        return self._latest_route_complete

    def start(self) -> None:
        self._dispatcher.start()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
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
        self._latest_position = point
        bearing_rad: float | None = None
        reference = self._course_reference
        if reference is None:
            self._course_reference = point
        else:
            distance_m = self._distance_m(reference, point)
            if distance_m >= _MIN_COURSE_POSITION_DELTA_M:
                bearing_rad = self._bearing_rad(reference, point)
                self._course_reference = point
                if self._latest_course_rad is None:
                    self._latest_heading_rad = bearing_rad
        self._handler.update_follow_camera(point, bearing_rad)
        self._renderer_client.set_position(
            latitude=math.degrees(data.latitude_rad),
            longitude=math.degrees(data.longitude_rad),
        )

    def _on_motion_message(self, message: MotionStateMessage) -> None:
        data = message.data
        self._latest_ground_speed_m_s = data.ground_speed_m_s
        self._latest_course_rad = data.course_rad
        self._latest_heading_rad = data.heading_rad
        speed_m_s = data.ground_speed_m_s
        if speed_m_s is None or speed_m_s < _MIN_COURSE_UP_SPEED_M_S:
            return
        bearing_rad = data.course_rad if data.course_rad is not None else data.heading_rad
        if bearing_rad is not None:
            self._handler.update_follow_bearing(bearing_rad)

    def _on_route_guidance_message(self, message: RouteGuidanceStateMessage) -> None:
        data = message.data
        self._latest_instruction = data.instruction
        self._latest_distance_to_maneuver_m = data.distance_to_maneuver_m
        self._latest_distance_remaining_m = data.distance_remaining_m
        self._latest_off_route = data.off_route
        self._latest_route_complete = data.route_complete

    @staticmethod
    def _distance_m(start: GeoPoint, end: GeoPoint) -> float:
        d_lat = end.latitude_rad - start.latitude_rad
        d_lon = end.longitude_rad - start.longitude_rad
        sin_lat = math.sin(d_lat / 2.0)
        sin_lon = math.sin(d_lon / 2.0)
        a = (
            sin_lat * sin_lat
            + math.cos(start.latitude_rad)
            * math.cos(end.latitude_rad)
            * sin_lon
            * sin_lon
        )
        return 2.0 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))

    @staticmethod
    def _bearing_rad(start: GeoPoint, end: GeoPoint) -> float:
        d_lon = end.longitude_rad - start.longitude_rad
        y = math.sin(d_lon) * math.cos(end.latitude_rad)
        x = (
            math.cos(start.latitude_rad) * math.sin(end.latitude_rad)
            - math.sin(start.latitude_rad)
            * math.cos(end.latitude_rad)
            * math.cos(d_lon)
        )
        return math.atan2(y, x)
