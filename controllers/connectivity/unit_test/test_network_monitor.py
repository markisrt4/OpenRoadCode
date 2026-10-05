# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Local network sources report unknown when monitoring is unavailable."""
import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from controllers.connectivity.network_monitor import (
    NetworkMonitor, android_network_state, linux_network_state,
)


@pytest.mark.parametrize('state,expected', [
    ({'available': True, 'connected': True, 'validated': True}, True),
    ({'available': True, 'connected': True, 'validated': False}, False),
    ({'available': True, 'connected': False, 'validated': False}, False),
    ({'available': False}, None),
    ({'available': True, 'connected': 'false', 'validated': True}, None),
    ({}, None),
])
def test_android_uses_only_validated_networks_and_bypasses_proxies(state, expected):
    with patch('controllers.connectivity.network_monitor.urllib.request.build_opener') as factory:
        factory.return_value.open.return_value.__enter__.return_value.read.return_value = json.dumps(state).encode()
        assert android_network_state() is expected
        assert factory.call_args.args[0].proxies == {}
        factory.return_value.open.assert_called_once_with('http://127.0.0.1:8766/network', timeout=0.75)


def test_old_or_stopped_bridge_allows_internet_fallback():
    with patch('controllers.connectivity.network_monitor.urllib.request.build_opener') as factory:
        factory.return_value.open.side_effect = OSError('connection refused')
        assert android_network_state() is None


@pytest.mark.parametrize('output,expected', [
    ('connected:full\n', True), ('connected:unknown\n', True),
    ('disconnected:none\n', False), ('asleep:none\n', False),
    ('connected (local only):none\n', False), ('connected (site only):limited\n', False),
    ('connected:portal\n', False), ('unexpected:unknown\n', None),
])
def test_network_manager_states(output, expected):
    with patch('controllers.connectivity.network_monitor.subprocess.run',
               return_value=subprocess.CompletedProcess([], 0, output, '')) as run:
        assert linux_network_state('/usr/bin/nmcli') is expected
        assert run.call_args.kwargs['timeout'] == 2
        assert run.call_args.kwargs['env']['LC_ALL'] == 'C'


def test_absent_network_manager_returns_unknown():
    with patch('controllers.connectivity.network_monitor.subprocess.run',
               return_value=subprocess.CompletedProcess([], 1, '', 'not running')):
        assert linux_network_state('nmcli') is None


def test_monitor_emits_only_changes_and_not_after_shutdown():
    notify = Mock()
    monitor = NetworkMonitor(notify)
    monitor._emit(None)
    monitor._emit(None)
    monitor._emit(False)
    monitor._emit(False)
    monitor._emit(True)
    assert [call.args[0] for call in notify.call_args_list] == [None, False, True]
    monitor.close()
    monitor._emit(False)
    assert notify.call_count == 3


def test_linux_monitor_reads_initial_state_and_reacts_to_dbus_events():
    notify = Mock()
    monitor = NetworkMonitor(notify)
    process = Mock()
    process.stdout = iter(('network changed\n', 'network changed again\n'))
    process.poll.return_value = 0
    # End after the monitor exits, without sleeping/restarting it in the test.
    monitor._terminate = Mock(side_effect=lambda _: monitor._stop.set())
    with patch('controllers.connectivity.network_monitor.os.path.exists', return_value=False), patch.dict(
            'os.environ', {'TERMUX_VERSION': ''}), patch(
            'controllers.connectivity.network_monitor.shutil.which', return_value='/usr/bin/nmcli'), patch(
            'controllers.connectivity.network_monitor.linux_network_state', side_effect=(True, False, True)), patch(
            'controllers.connectivity.network_monitor.subprocess.Popen', return_value=process) as launch:
        monitor._run()
    assert [call.args[0] for call in notify.call_args_list] == [True, False, True]
    assert launch.call_args.args[0] == ['/usr/bin/nmcli', 'monitor']


def test_close_terminates_monitor_process():
    monitor = NetworkMonitor(Mock())
    process = Mock()
    process.poll.return_value = None
    monitor._process = process
    monitor.close()
    process.terminate.assert_called_once()
    process.wait.assert_called_once_with(timeout=0.5)
    process.stdout.close.assert_called_once()
