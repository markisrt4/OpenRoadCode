# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared ORCui camera runtime for native map panels."""

from __future__ import annotations

import math
import os
from pathlib import Path

from controllers.cache import PersistentCache
from controllers.map_renderer.map_request_handler import MapRequestHandler
from controllers.navigation.position_snapshot_cache import (
    DEFAULT_POSITION_CACHE_DIRECTORY,
    PositionSnapshotCache,
)
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
_EARTH_RADIUS_M = 6_378_137.0


class MapCameraRuntime:
    """Feed navigation position and motion into the native map camera."""

    def __init__(
        self,
        *,
        zoom_level: float = 16.5,
        pitch_rad: float = 0.0,
        follow_enabled: bool = True,
        position_cache_directory: str | Path | None = None,
    ) -> None:
        cached_center = self._load_cached_center(position_cache_directory)
        initial_center = cached_center or GeoPoint(
            latitude_rad=0.0,
            longitude_rad=0.0,
        )

        self._renderer_client = MapRendererClient()
        self._handler = MapRequestHandler(
            self._renderer_client,
            center=initial_center,
            zoom_level=zoom_level,
            pitch_rad=pitch_rad,
            follow_enabled=follow_enabled,
            camera_initialized=cached_center is not None,
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
        self._course_reference: GeoPoint | None = cached_center
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

        # Android location providers do not always report speed/course even
        # while position itself is updating. Derive a stable course from the
        # displacement between sufficiently separated fixes so course-up still
        # works on those providers without letting stationary GPS noise spin
        # the map. When a new course is available, apply it with the new center
        # in one camera command rather than rendering two successive jumps.
        bearing_rad: float | None = None
        reference = self._course_reference
        if reference is None:
            self._course_reference = point
        else:
            distance_m = self._distance_m(reference, point)
            if distance_m >= _MIN_COURSE_POSITION_DELTA_M:
                bearing_rad = self._bearing_rad(reference, point)
                self._course_reference = point

        self._handler.update_follow_camera(point, bearing_rad)

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

    @staticmethod
    def _load_cached_center(
        position_cache_directory: str | Path | None,
    ) -> GeoPoint | None:
        directory = (
            Path(position_cache_directory).expanduser()
            if position_cache_directory is not None
            else Path(
                os.getenv(
                    "CARUI_POSITION_CACHE_DIRECTORY",
                    str(DEFAULT_POSITION_CACHE_DIRECTORY),
                )
            ).expanduser()
        )
        try:
            cached = PositionSnapshotCache(PersistentCache(directory)).load()
        except OSError:
            return None

        if (
            cached is None
            or cached.latitude_deg is None
            or cached.longitude_deg is None
        ):
            return None

        return GeoPoint(
            latitude_rad=math.radians(cached.latitude_deg),
            longitude_rad=math.radians(cached.longitude_deg),
            altitude_m=cached.altitude_m,
        )

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
