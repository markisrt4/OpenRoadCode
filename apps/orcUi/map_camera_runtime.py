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
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT
from protocols.map_renderer.map_renderer_client import MapRendererClient
from ui.navigation import GeoPoint, MapRequestHandlerIf

_MIN_COURSE_UP_SPEED_M_S = 1.5


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
        self._dispatcher = MessageDispatcher(
            ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT)
        )
        self._dispatcher.register(
            POSITION_STATE_TOPIC,
            decode_position_state,
            self._on_position_message,
        )
        self._dispatcher.register(
            MOTION_STATE_TOPIC,
            decode_motion_state,
            self._on_motion_message,
        )
        self._closed = False

    @property
    def request_handler(self) -> MapRequestHandlerIf:
        """Return the semantic camera request interface."""

        return self._handler

    def start(self) -> None:
        """Start receiving navigation position and motion updates."""

        self._dispatcher.start()

    def close(self) -> None:
        """Release subscriber and renderer-command resources."""

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
        self._handler.update_follow_center(point)

        # Position and camera are deliberately separate renderer commands. The
        # marker remains at the vehicle's true location while the user pans or
        # disables follow mode.
        self._renderer_client.set_position(
            latitude=math.degrees(data.latitude_rad),
            longitude=math.degrees(data.longitude_rad),
        )

    def _on_motion_message(self, message: MotionStateMessage) -> None:
        """Keep a followed map course-up while the vehicle is moving."""
        data = message.data
        speed_m_s = data.ground_speed_m_s
        if speed_m_s is None or speed_m_s < _MIN_COURSE_UP_SPEED_M_S:
            return

        bearing_rad = data.course_rad
        if bearing_rad is None:
            bearing_rad = data.heading_rad
        if bearing_rad is None:
            return

        self._handler.update_follow_bearing(bearing_rad)
