# SPDX-License-Identifier: MIT

"""Playback snapshots stay responsive and retirement prevents late native launch."""

import threading
from unittest.mock import Mock

import pytest

from controllers.audio.streaming_audio_player_if import StreamingAudioPlayerIf
from controllers.radio.streaming_radio_controller import StreamingRadioController
from ui.radio.streaming_radio_types import StreamingRadioStation


STATION = StreamingRadioStation("one", "One", "https://radio.test/one")


def test_snapshot_does_not_wait_for_playback_and_stop_is_serialized():
    player = Mock(spec=StreamingAudioPlayerIf)
    player.is_playing = False
    entered, release, stop_requested = threading.Event(), threading.Event(), threading.Event()
    calls = []
    def play(url):
        entered.set()
        assert release.wait(3)
        calls.append("play")
        player.is_playing = True
    def stop():
        calls.append("stop")
        player.is_playing = False
    player.play.side_effect = play
    player.stop.side_effect = stop
    controller = StreamingRadioController(player)
    errors = []
    def start():
        try:
            controller.play(STATION)
        except Exception as error:
            errors.append(error)
    play_thread = threading.Thread(target=start)
    play_thread.start()
    assert entered.wait(3)
    def request_stop():
        stop_requested.set()
        controller.stop()
    stop_thread = threading.Thread(target=request_stop)
    stop_thread.start()
    assert stop_requested.wait(3)
    try:
        snapshot = controller.snapshot()
        assert not snapshot.is_playing and snapshot.station is None
        player.stop.assert_not_called()
    finally:
        release.set()
        play_thread.join(3)
        stop_thread.join(3)
    assert not play_thread.is_alive() and not stop_thread.is_alive()
    assert errors == [] and calls == ["play", "stop"]
    assert not controller.snapshot().is_playing


def test_terminal_close_waits_for_startup_and_rejects_late_playback():
    player = Mock(spec=StreamingAudioPlayerIf)
    player.is_playing = False
    entered, release, closing = threading.Event(), threading.Event(), threading.Event()
    def play(url):
        entered.set()
        assert release.wait(3)
        player.is_playing = True
    player.play.side_effect = play
    player.stop.side_effect = lambda: setattr(player, "is_playing", False)
    controller = StreamingRadioController(player)
    start_thread = threading.Thread(target=lambda: controller.play(STATION))
    start_thread.start()
    assert entered.wait(3)
    def close():
        closing.set()
        controller.close()
    close_thread = threading.Thread(target=close)
    close_thread.start()
    assert closing.wait(3)
    release.set()
    start_thread.join(3)
    close_thread.join(3)
    assert not start_thread.is_alive() and not close_thread.is_alive()
    assert not controller.snapshot().is_playing
    with pytest.raises(RuntimeError, match="closed"):
        controller.play(STATION)
    controller.close()
    player.stop.assert_called_once()
    player.play.assert_called_once()


def test_failed_close_still_retires_future_playback():
    player = Mock(spec=StreamingAudioPlayerIf)
    controller = StreamingRadioController(player)
    player.stop.side_effect = OSError("native stop failed")
    with pytest.raises(OSError, match="native stop failed"):
        controller.close()
    with pytest.raises(RuntimeError, match="closed"):
        controller.play(STATION)
    player.play.assert_not_called()


def test_delayed_offline_stop_does_not_stop_playback_after_returning_online():
    player = Mock(spec=StreamingAudioPlayerIf)
    player.is_playing = True
    controller = StreamingRadioController(player)
    online = [True]
    controller.set_network_allowed(lambda: online[0])
    controller.play(STATION)
    online[0] = False
    stop_worker = controller.stop_if_offline  # Composition queues this work.
    online[0] = True
    stop_worker()
    player.stop.assert_not_called()
    assert controller.snapshot().is_playing
    online[0] = False
    stop_worker()
    player.stop.assert_called_once()
    assert controller.snapshot().station is None
