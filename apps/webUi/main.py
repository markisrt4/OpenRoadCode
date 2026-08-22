# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode browser application bootstrap."""

import atexit
import os

from apps.webUi.menu_catalog import create_web_ui_menu_pages
from apps.webUi.navigation_session import WebNavigationSession
from apps.webUi.periodic_position_publisher import PeriodicPositionPublisher
from apps.webUi.spotify_session import WebSpotifySession
from frontends.web import create_web_frontend
from messaging.contracts.navigation import PositionStatePublisher
from messaging.zeromq import ZeroMqPublisher


def _create_navigation_session() -> tuple[
    WebNavigationSession,
    ZeroMqPublisher | None,
    PeriodicPositionPublisher | None,
]:
    """Create WebUi navigation state and optional steady ZeroMQ publication."""
    enabled = os.environ.get("OPENROADCODE_ZMQ_POSITION_PUBLISH", "0") == "1"
    if not enabled:
        return WebNavigationSession(), None, None

    endpoint = os.environ.get(
        "OPENROADCODE_ZMQ_POSITION_ENDPOINT",
        "tcp://0.0.0.0:5557",
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


navigation_session, position_zmq_publisher, periodic_position_publisher = _create_navigation_session()
spotify_session = WebSpotifySession()
app = create_web_frontend(
    create_web_ui_menu_pages(),
    navigation_session=navigation_session,
    spotify_session=spotify_session,
)


def _close_position_messaging() -> None:
    if periodic_position_publisher is not None:
        periodic_position_publisher.close()
    if position_zmq_publisher is not None:
        position_zmq_publisher.close()


atexit.register(_close_position_messaging)


if __name__ == "__main__":
    host = os.environ.get("OPENROADCODE_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("OPENROADCODE_WEB_PORT", "5000"))
    debug = os.environ.get("OPENROADCODE_WEB_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
