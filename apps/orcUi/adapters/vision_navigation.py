# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Wire existing navigation topics and displayed camera frames into the overlay."""

import time

from controllers.computer_vision.navigation_overlay_controller import NavigationOverlayController
from messaging.contracts.navigation import (
    MOTION_STATE_TOPIC, POSITION_STATE_TOPIC, MotionStateMessage, PositionStateMessage,
    decode_motion_state, decode_position_state,
)
from messaging.contracts.route_guidance import (
    ROUTE_GUIDANCE_STATE_TOPIC, RouteGuidanceStateMessage, decode_route_guidance_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT
from ui.navigation.route_types import RouteTurn
from ui.vision.navigation_overlay import OverlayGuidance, OverlayMotion, OverlayPosition
from ui.vision.vision_request_handler_if import VisionRequestHandlerIf
from ui.vision.vision_ui_if import VisionUiIf
from ui.vision.vision_ui_state import VisionUiState


class VisionNavigationUiAdapter(VisionUiIf):
    """Observe delivered frames at composition, without exposing controllers to widgets."""

    def __init__(self, ui: VisionUiIf, navigation: NavigationOverlayController) -> None:
        self._ui = ui
        self._navigation = navigation

    def set_vision_request_handler(self, handler: VisionRequestHandlerIf | None) -> None:
        self._ui.set_vision_request_handler(handler)

    def set_vision_state(self, state: VisionUiState) -> None:
        self._ui.set_vision_state(state)
        # Present the image first: Tk may flush idle redraws during resizing.
        # Publishing the new HUD before that could put future hints on old video.
        self._navigation.set_frame(None if state.image is None else state.image.timestamp_s)


class VisionNavigationIngress:
    """Own one lazy, ordered topic subscriber; no camera or routing side effects."""

    def __init__(self, navigation: NavigationOverlayController) -> None:
        self._navigation = navigation
        self._dispatcher: MessageDispatcher | None = None
        self._position_stamp: tuple[int, int] | None = None
        self._motion_stamp: tuple[int, int] | None = None
        self._closed = False

    def start(self) -> None:
        if self._closed or self._dispatcher is not None:
            return
        dispatcher = MessageDispatcher(ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT), max_workers=1)
        self._dispatcher = dispatcher
        dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, self._on_position)
        dispatcher.register(MOTION_STATE_TOPIC, decode_motion_state, self._on_motion)
        dispatcher.register(ROUTE_GUIDANCE_STATE_TOPIC, decode_route_guidance_state, self._on_guidance)
        dispatcher.start()

    def close(self) -> None:
        self._closed = True
        if self._dispatcher is not None:
            self._dispatcher.close()
            self._dispatcher = None

    def _on_position(self, message: PositionStateMessage) -> None:
        if self._closed:
            return
        stamp = (message.timestamp.seconds, message.timestamp.nanoseconds)
        if self._position_stamp is not None and stamp <= self._position_stamp:
            return
        self._position_stamp = stamp
        data = message.data
        has_fix = (data.fix_mode is not None and data.fix_mode >= 2
                   and data.latitude_rad is not None and data.longitude_rad is not None)
        self._navigation.update_position(OverlayPosition(
            time.monotonic(), has_fix, data.is_cached, data.accuracy_m,
        ))

    def _on_motion(self, message: MotionStateMessage) -> None:
        if self._closed:
            return
        stamp = (message.timestamp.seconds, message.timestamp.nanoseconds)
        if self._motion_stamp is not None and stamp <= self._motion_stamp:
            return
        self._motion_stamp = stamp
        self._navigation.update_motion(OverlayMotion(
            time.monotonic(), message.data.ground_speed_m_s, message.data.is_cached,
        ))

    def _on_guidance(self, message: RouteGuidanceStateMessage) -> None:
        if self._closed:
            return
        data = message.data
        self._navigation.update_guidance(OverlayGuidance(
            timestamp_s=time.monotonic(), instruction=data.instruction,
            turn=RouteTurn(data.turn), road_name=data.road_name,
            distance_m=data.distance_to_maneuver_m, off_route=data.off_route,
            complete=data.route_complete,
        ))
