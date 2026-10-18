# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Fresh GPS, Waze-only targets and browser-session cancellation."""
from contextlib import contextmanager
import math
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from controllers.navigation.waze_location_player import WazeLocationPlayer
from ui.navigation import GeoPoint


def test_live_si_fix_conversion_expiry_and_invalidation():
    clock = Mock(return_value=100.0)
    player = WazeLocationPlayer(Mock(), clock=clock)
    assert player._params() == {}
    player.update_position(GeoPoint(math.radians(42), math.radians(-83), 120))
    assert player._params() == {'latitude': 42, 'longitude': -83, 'accuracy': 50, 'altitude': 120}
    clock.return_value = 111
    assert player._params() == {}
    player.update_position(GeoPoint(0, 0))
    player.update_position(None)
    assert player._params() == {}


@pytest.mark.parametrize('point', [GeoPoint(float('nan'), 0), GeoPoint(0, float('inf')),
                                   GeoPoint(math.pi, 0), GeoPoint(0, 4)])
def test_invalid_fix_is_not_delivered(point):
    player = WazeLocationPlayer(Mock())
    player.update_position(point)
    assert player._params() == {}


@pytest.mark.parametrize('origin, path', [
    ('https://www.waze.com', '/live-map'),
    ('https://embed.waze.com', '/iframe'),
])
def test_retains_connection_until_stop_and_skips_unrelated_pages(origin, path):
    stop = Event()
    commands = []
    closed = []
    session = Mock()
    def command(method, params):
        commands.append((method, params))
        if method == 'Emulation.setGeolocationOverride':
            assert not closed
            stop.set()
    session.command.side_effect = command
    @contextmanager
    def connect(target):
        assert target.url == origin + path
        try:
            yield session
        finally:
            closed.append(True)
    client = Mock()
    client.targets.return_value = [SimpleNamespace(id='page', url='https://example.com'),
        SimpleNamespace(id='page', url='https://www.waze.com.attacker.example'),
        SimpleNamespace(id='page', url=origin + path)]
    client.session.side_effect = connect
    player = WazeLocationPlayer(Mock(), client=client)
    player.update_position(GeoPoint(0, 0))
    player._run(stop)
    assert commands[0] == ('Browser.grantPermissions', {
        'origin': origin, 'permissions': ['geolocation']})
    assert commands[1][0] == 'Emulation.setGeolocationOverride'
    assert closed == [True]


def test_stop_waits_for_inflight_command_before_closing_browser():
    entered, release, stopped = Event(), Event(), Event()
    browser = Mock()
    player = WazeLocationPlayer(browser)
    def worker():
        entered.set()
        release.wait(2)
    player._thread = Thread(target=worker)
    player._thread.start()
    assert entered.wait(1)
    shutdown = Thread(target=lambda: (player.stop(), stopped.set()))
    shutdown.start()
    try:
        assert player._stop.wait(1)
        browser.stop.assert_not_called()
    finally:
        release.set()
        shutdown.join(2)
    assert stopped.is_set()
    browser.stop.assert_called_once()


def test_cancelled_launch_does_not_start_worker_and_closed_player_ignores_updates():
    browser = Mock()
    browser.play.return_value = False
    player = WazeLocationPlayer(browser)
    assert not player.play('https://embed.waze.com/iframe', display=':0')
    assert player._thread is None
    player.close()
    player.update_position(GeoPoint(0, 0))
    assert not player.play('https://embed.waze.com/iframe', display=':0')
    browser.play.assert_called_once()
    assert player._params() == {}
