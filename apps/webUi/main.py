# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode browser application bootstrap."""

import atexit
import os

from apps.webUi.menu_catalog import create_web_ui_menu_pages
from apps.webUi.navigation_session import WebNavigationSession
from apps.webUi.periodic_position_publisher import PeriodicPositionPublisher
from apps.webUi.spotify_session import WebSpotifySession
from apps.webUi.web_navigation_ui_state import WebNavigationUiState
from frontends.web import create_web_frontend
from messaging.contracts.navigation import (
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    PositionStatePublisher,
    decode_motion_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqPublisher, ZeroMqSubscriber


def _create_navigation_session() -> tuple[
    WebNavigationSession,
    ZeroMqPublisher | None,
    PeriodicPositionPublisher | None,
]:
    """Create WebUI browser navigation producer and optional ZMQ publication."""
    enabled = os.environ.get("OPENROADCODE_ZMQ_POSITION_PUBLISH", "0") == "1"
    if not enabled:
        return WebNavigationSession(), None, None

    endpoint = os.environ.get(
        "OPENROADCODE_ZMQ_POSITION_ENDPOINT",
        "tcp://127.0.0.1:5556",
    )
    rate_hz = float(os.environ.get("OPENROADCODE_ZMQ_POSITION_RATE_HZ", "5.0"))

    publisher = ZeroMqPublisher(endpoint)
    position_publisher = PositionStatePublisher(publisher)
    periodic_publisher = PeriodicPositionPublisher(
        position_publisher.publish,
        rate_hz=rate_hz,
    )
    periodic_publisher.start()

    return (
        WebNavigationSession(position_sink=periodic_publisher.update),
        publisher,
        periodic_publisher,
    )


def _create_navigation_consumer() -> tuple[WebNavigationUiState, MessageDispatcher]:
    """Consume public navigation contracts for the WebUI presentation model."""
    endpoint = os.environ.get(
        "OPENROADCODE_ZMQ_NAVIGATION_SUBSCRIBE_ENDPOINT",
        "tcp://127.0.0.1:5557",
    )
    ui_state = WebNavigationUiState()
    dispatcher = MessageDispatcher(
        ZeroMqSubscriber(endpoint),
        error_handler=ui_state.set_error,
    )
    dispatcher.register(
        POSITION_STATE_TOPIC,
        decode_position_state,
        ui_state.set_position,
    )
    dispatcher.register(
        MOTION_STATE_TOPIC,
        decode_motion_state,
        ui_state.set_motion,
    )
    dispatcher.start()
    return ui_state, dispatcher


navigation_session, position_zmq_publisher, periodic_position_publisher = _create_navigation_session()
navigation_ui_state, navigation_dispatcher = _create_navigation_consumer()
spotify_session = WebSpotifySession()
app = create_web_frontend(
    create_web_ui_menu_pages(),
    navigation_session=navigation_session,
    navigation_ui_state=navigation_ui_state,
    spotify_session=spotify_session,
)


def _close_messaging() -> None:
    navigation_dispatcher.close()
    if periodic_position_publisher is not None:
        periodic_position_publisher.close()
    if position_zmq_publisher is not None:
        position_zmq_publisher.close()


atexit.register(_close_messaging)


if __name__ == "__main__":
    host = os.environ.get("OPENROADCODE_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("OPENROADCODE_WEB_PORT", "5000"))
    debug = os.environ.get("OPENROADCODE_WEB_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
