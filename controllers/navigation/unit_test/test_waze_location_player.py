# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Fresh GPS, Waze-only targets and browser-session cancellation."""
from contextlib import contextmanager
import math
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock

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
            if sum(command[0] == method for command in commands) == 2:
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
    client.targets.return_value = [SimpleNamespace(id='other', url='https://example.com'),
        SimpleNamespace(id='attacker', url='https://www.waze.com.attacker.example'),
        SimpleNamespace(id='page', url=origin + path)]
    client.session.side_effect = connect
    player = WazeLocationPlayer(Mock(), client=client)
    player.update_position(GeoPoint(0, 0))
    player._run(stop)
    assert commands[0][0] == 'Emulation.setGeolocationOverride'
    assert commands[1] == ('Browser.grantPermissions', {
        'origin': origin, 'permissions': ['geolocation']})
    assert commands[2][0] == 'Emulation.setGeolocationOverride'
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


class ImmediateStop:
    """Deterministic polling without sleeping in worker behavior tests."""
    def __init__(self):
        self.stopped = False

    def is_set(self):
        return self.stopped

    def set(self):
        self.stopped = True

    def wait(self, _seconds):
        return self.stopped


def test_direct_start_installs_provider_and_permission_before_reload():
    stop, client, session = ImmediateStop(), Mock(), Mock()
    client.targets.side_effect = [
        [SimpleNamespace(id='owned', url='https://www.waze.com/live-map')],
        [SimpleNamespace(id='owned', url='')],
        [SimpleNamespace(id='owned', url='https://www.waze.com/live-map')],
        [SimpleNamespace(id='owned', url='https://www.waze.com/live-map/directions?to=home')],
    ]
    client.session.return_value = MagicMock()
    client.session.return_value.__enter__.return_value = session
    session.command.return_value = {}
    commands = []
    def command(method, params):
        commands.append((method, params))
        if len(commands) == 6:
            stop.set()
        return {}
    session.command.side_effect = command
    player = WazeLocationPlayer(Mock(), client=client)
    player.update_position(GeoPoint(0, 0))
    player._run(stop, 'https://www.waze.com/live-map')
    assert [method for method, _ in commands[:3]] == [
        'Emulation.setGeolocationOverride', 'Browser.grantPermissions', 'Page.reload',
    ]
    assert commands[1][1]['origin'] == 'https://www.waze.com'
    assert commands[2][1] == {'ignoreCache': False}
    client.session.assert_called_once()
    client.session.return_value.__exit__.assert_called_once()


def test_same_origin_route_changes_retain_permission_session():
    stop, client, session = ImmediateStop(), Mock(), Mock()
    urls = ('https://www.waze.com/live-map', '',
            'https://www.waze.com/live-map/directions?to=home',
            'https://www.waze.com/live-map?from=current&to=home')
    client.targets.side_effect = [[SimpleNamespace(id='owned', url=url)] for url in urls]
    client.session.return_value = MagicMock()
    client.session.return_value.__enter__.return_value = session
    def command(method, params):
        if session.command.call_count == 5:
            stop.set()
        return {}
    session.command.side_effect = command
    WazeLocationPlayer(Mock(), client=client)._run(stop)
    client.session.assert_called_once()
    assert sum(call.args[0] == 'Browser.grantPermissions' for call in session.command.call_args_list) == 1
    assert session.command.call_count == 5


def test_cross_origin_navigation_closes_permission_session():
    stop, client, session = ImmediateStop(), Mock(), Mock()
    client.targets.side_effect = [
        [SimpleNamespace(id='owned', url='https://www.waze.com/live-map')],
        [SimpleNamespace(id='owned', url='https://example.com/')],
    ]
    @contextmanager
    def connect(target):
        try:
            yield session
        finally:
            stop.set()
    client.session.side_effect = connect
    WazeLocationPlayer(Mock(), client=client)._run(stop)
    assert [call.args[0] for call in session.command.call_args_list] == [
        'Emulation.setGeolocationOverride', 'Browser.grantPermissions',
    ]


def test_play_opens_real_waze_and_waits_for_control_readiness():
    from unittest.mock import patch
    browser = Mock()
    browser.play.return_value = True
    player = WazeLocationPlayer(browser)
    with patch('controllers.navigation.waze_location_player.Thread') as thread:
        thread.return_value.start.side_effect = lambda: (player._ready.set(), player._startup_complete.set())
        assert player.play('https://www.waze.com/live-map', display=':1')
        assert browser.play.call_args.args == ('https://www.waze.com/live-map',)
        assert thread.call_args.kwargs['args'][1] == 'https://www.waze.com/live-map'
        thread.return_value.start.assert_called_once()
        player.stop()
        thread.return_value.join.assert_called_once()


def test_stop_during_bootstrap_never_grants_or_navigates_after_hide():
    stop, client, session = ImmediateStop(), Mock(), Mock()
    client.targets.return_value = [SimpleNamespace(id='owned', url='https://www.waze.com/live-map')]
    client.session.return_value = MagicMock()
    client.session.return_value.__enter__.return_value = session
    session.command.side_effect = lambda *_args: stop.set()
    WazeLocationPlayer(Mock(), client=client)._run(stop, 'https://www.waze.com/live-map')
    assert [call.args[0] for call in session.command.call_args_list] == [
        'Emulation.setGeolocationOverride',
    ]
    client.session.return_value.__exit__.assert_called_once()


def test_theme_refresh_switches_both_preferences_without_navigation_or_duplicate_commands():
    scheme, session, stop = ['dark'], Mock(), ImmediateStop()
    player = WazeLocationPlayer(Mock(), preferred_color_scheme=lambda: scheme[0])
    applied = player._apply_theme(session, None, stop)
    assert applied == 'dark'
    assert session.command.call_args_list[0].args == ('Emulation.setEmulatedMedia', {
        'features': [{'name': 'prefers-color-scheme', 'value': 'dark'}],
    })
    assert session.command.call_args_list[1].args == ('Emulation.setAutoDarkModeOverride', {'enabled': True})
    player._apply_theme(session, applied, stop)
    assert session.command.call_count == 2
    scheme[0] = 'light'
    applied = player._apply_theme(session, applied, stop)
    assert applied == 'light'
    assert session.command.call_args.args == ('Emulation.setAutoDarkModeOverride', {'enabled': False})
    player.request_theme_refresh()
    player._apply_theme(session, applied, stop)
    assert session.command.call_count == 6
    assert not any(call.args[0] == 'Page.navigate' for call in session.command.call_args_list)


def test_unsupported_auto_dark_does_not_interrupt_location_permission_or_updates():
    stop, client, session = ImmediateStop(), Mock(), Mock()
    client.targets.return_value = [SimpleNamespace(id='owned', url='https://www.waze.com/live-map')]
    client.session.return_value = MagicMock()
    client.session.return_value.__enter__.return_value = session
    commands = []
    def command(method, params):
        commands.append(method)
        if method == 'Emulation.setAutoDarkModeOverride':
            raise RuntimeError('Method not found')
        if commands.count('Emulation.setGeolocationOverride') == 2:
            stop.set()
        return {}
    session.command.side_effect = command
    player = WazeLocationPlayer(Mock(), client=client, preferred_color_scheme=lambda: 'dark')
    player._run(stop)
    assert 'Browser.grantPermissions' in commands
    assert commands.count('Emulation.setGeolocationOverride') == 2
    assert commands.count('Emulation.setAutoDarkModeOverride') == 1


def test_stopped_session_does_not_apply_pending_theme():
    stop, session = ImmediateStop(), Mock()
    player = WazeLocationPlayer(Mock(), preferred_color_scheme=lambda: 'dark')
    stop.set()
    player.request_theme_refresh()
    player._apply_theme(session, None, stop)
    session.command.assert_not_called()


def test_control_startup_timeout_stops_browser_instead_of_claiming_ready():
    from unittest.mock import patch
    browser = Mock()
    browser.play.return_value = True
    player = WazeLocationPlayer(browser, startup_timeout_seconds=0.001)
    with patch('controllers.navigation.waze_location_player.Thread') as thread:
        with pytest.raises(RuntimeError, match='did not become ready'):
            player.play('https://www.waze.com/live-map', display=':1')
        thread.return_value.join.assert_called_once()
    assert not player._ready.is_set()
    assert browser.stop.call_count == 2


def test_new_tab_page_is_not_accepted_as_a_ready_waze_target():
    class StopAfterPoll(ImmediateStop):
        def wait(self, _seconds):
            self.set()
            return True
    stop, client = StopAfterPoll(), Mock()
    client.targets.return_value = [SimpleNamespace(id='newtab', url='chrome://newtab/')]
    player = WazeLocationPlayer(Mock(), client=client)
    player._run(stop, 'https://www.waze.com/live-map')
    assert not player._ready.is_set()
    client.session.assert_not_called()
