# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import Mock, patch
import pytest

from apps.launchers.host_location_session import HostLocationSession, HostLocationSessionError
from services.navigation.navigation_command_client import NavigationCommandUnavailableError


def test_existing_navigation_is_reused_without_starting_or_stopping_services():
    client = Mock()
    session = HostLocationSession(client)
    with patch('apps.launchers.host_location_session.subprocess.Popen') as spawn:
        session.start()
        session.close()
    client.prepare_host_location.assert_called_once_with()
    spawn.assert_not_called()


def test_user_session_starts_local_services_without_sudo_and_stops_only_owned_children():
    client = Mock()
    client.prepare_host_location.side_effect = [NavigationCommandUnavailableError('offline'),
                                               NavigationCommandUnavailableError('starting'), None, None]
    session = HostLocationSession(client)
    session._listening = lambda port: False
    broker, navigation = Mock(), Mock()
    broker.poll.return_value = navigation.poll.return_value = None
    with patch('apps.launchers.host_location_session.subprocess.Popen', side_effect=[broker, navigation]) as spawn, \
            patch('apps.launchers.host_location_session.Thread'):
        session.start()
        session.start()
        assert spawn.call_count == 2
        assert client.prepare_host_location.call_count == 4
        commands = [call.args[0] for call in spawn.call_args_list]
        assert 'sudo' not in str(commands)
        assert 'tcp://127.0.0.1:5556' in commands[0]
        session.close()
        session.close()
        broker.terminate.assert_called_once_with()
        navigation.terminate.assert_called_once_with()
        navigation.wait.assert_not_called()


def test_busy_existing_command_port_never_starts_a_duplicate_navigation():
    client = Mock()
    client.prepare_host_location.side_effect = NavigationCommandUnavailableError('busy')
    session = HostLocationSession(client)
    session._listening = lambda port: True
    with patch('apps.launchers.host_location_session.subprocess.Popen') as spawn:
        with pytest.raises(HostLocationSessionError, match='busy'):
            session.start()
    spawn.assert_not_called()
