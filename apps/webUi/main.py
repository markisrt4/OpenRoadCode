# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode browser application bootstrap."""

import atexit
import os

from apps.webUi.browser_music_analysis_session import WebBrowserMusicAnalysisSession
from apps.webUi.linux_audio_analysis_session import WebLinuxAudioAnalysisSession
from apps.webUi.menu_catalog import create_web_ui_menu_pages
from apps.webUi.music_reactive_lighting_session import WebMusicReactiveLightingSession
from apps.webUi.navigation_session import WebNavigationSession
from apps.webUi.periodic_position_publisher import PeriodicPositionPublisher
from apps.webUi.song_recognition_session import WebSongRecognitionSession
from apps.webUi.spotify_session import WebSpotifySession
from apps.webUi.web_navigation_ui_state import WebNavigationUiState
from apps.webUi.web_vehicle_ui_state import WebVehicleUiState
from controllers.audio.music_analysis import MusicAnalysisFanout
from controllers.lighting import DummyLightingController, MusicReactiveLighting
from frontends.web import create_web_frontend
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
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

    endpoint = os.environ.get("OPENROADCODE_ZMQ_POSITION_ENDPOINT", "tcp://127.0.0.1:5556")
    rate_hz = float(os.environ.get("OPENROADCODE_ZMQ_POSITION_RATE_HZ", "5.0"))
    publisher = ZeroMqPublisher(endpoint)
    position_publisher = PositionStatePublisher(publisher)
    periodic_publisher = PeriodicPositionPublisher(position_publisher.publish, rate_hz=rate_hz)
    periodic_publisher.start()
    return WebNavigationSession(position_sink=periodic_publisher.update), publisher, periodic_publisher


def _create_bus_consumer() -> tuple[WebNavigationUiState, WebVehicleUiState, MessageDispatcher]:
    """Consume public navigation and automotive contracts for WebUI models."""
    endpoint = os.environ.get("OPENROADCODE_ZMQ_SUBSCRIBE_ENDPOINT", os.environ.get("OPENROADCODE_ZMQ_NAVIGATION_SUBSCRIBE_ENDPOINT", "tcp://127.0.0.1:5557"))
    navigation_state = WebNavigationUiState()
    vehicle_state = WebVehicleUiState()

    def handle_error(topic: str, error: Exception) -> None:
        if topic == VEHICLE_STATE_TOPIC:
            vehicle_state.set_error(topic, error)
        else:
            navigation_state.set_error(topic, error)

    dispatcher = MessageDispatcher(ZeroMqSubscriber(endpoint), error_handler=handle_error)
    dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, navigation_state.set_position)
    dispatcher.register(MOTION_STATE_TOPIC, decode_motion_state, navigation_state.set_motion)
    dispatcher.register(VEHICLE_STATE_TOPIC, decode_vehicle_state, vehicle_state.set_vehicle)
    dispatcher.start()
    return navigation_state, vehicle_state, dispatcher


def _create_music_analysis() -> tuple[
    WebBrowserMusicAnalysisSession,
    WebLinuxAudioAnalysisSession,
    WebMusicReactiveLightingSession,
]:
    """Compose browser/Linux analysis with optional software-driven lighting."""
    if os.environ.get("OPENROADCODE_WEB_DUMMY_LIGHTING", "0") != "1":
        return (
            WebBrowserMusicAnalysisSession(),
            WebLinuxAudioAnalysisSession(),
            WebMusicReactiveLightingSession(),
        )

    controller = DummyLightingController()
    controller.connect().result()
    reactive_lighting = MusicReactiveLighting(controller)
    fanout = MusicAnalysisFanout((reactive_lighting.update,))
    return (
        WebBrowserMusicAnalysisSession(consumer=fanout),
        WebLinuxAudioAnalysisSession(consumer=fanout),
        WebMusicReactiveLightingSession(reactive_lighting),
    )


navigation_session, position_zmq_publisher, periodic_position_publisher = _create_navigation_session()
navigation_ui_state, vehicle_ui_state, bus_dispatcher = _create_bus_consumer()
spotify_session = WebSpotifySession()
song_recognition_session = WebSongRecognitionSession()
music_analysis_session, linux_music_analysis_session, music_reactive_lighting_session = _create_music_analysis()
app = create_web_frontend(
    create_web_ui_menu_pages(),
    navigation_session=navigation_session,
    navigation_ui_state=navigation_ui_state,
    vehicle_ui_state=vehicle_ui_state,
    spotify_session=spotify_session,
    music_analysis_session=music_analysis_session,
    linux_music_analysis_session=linux_music_analysis_session,
    music_reactive_lighting_session=music_reactive_lighting_session,
    song_recognition_session=song_recognition_session,
)


def _close_messaging() -> None:
    linux_music_analysis_session.stop()
    bus_dispatcher.close()
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
