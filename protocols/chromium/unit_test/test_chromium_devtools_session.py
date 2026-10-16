# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Retained CDP commands share and close their connection."""
import json
from unittest.mock import Mock, patch

import pytest

from protocols.chromium.chromium_devtools_client import ChromiumDevToolsClient, DevToolsTarget


def test_session_reuses_socket_skips_events_and_closes_on_exit():
    client = ChromiumDevToolsClient()
    socket = Mock()
    target = DevToolsTarget('page', 'Waze', 'https://embed.waze.com', 'ws://127.0.0.1:9224/page')
    with patch.object(client, '_connect_websocket') as connect, patch.object(
        client, '_send_text') as send, patch.object(client, '_receive_text', side_effect=[
            json.dumps({'method': 'Page.frameNavigated'}),
            json.dumps({'id': 1, 'result': {'ok': True}}),
            json.dumps({'id': 2, 'result': {}}),
        ]):
        connect.return_value.__enter__.return_value = socket
        with client.session(target) as session:
            assert session.command('Browser.grantPermissions', {}) == {'ok': True}
            assert session.command('Emulation.setGeolocationOverride', {}) == {}
            connect.return_value.__exit__.assert_not_called()
        connect.assert_called_once_with(target.web_socket_debugger_url)
        connect.return_value.__exit__.assert_called_once()
        assert [json.loads(call.args[1])['id'] for call in send.call_args_list] == [1, 2]
        assert all(call.args[0] is socket for call in send.call_args_list)


def test_session_surfaces_protocol_error_and_still_closes():
    client = ChromiumDevToolsClient()
    target = DevToolsTarget('page', '', '', 'ws://127.0.0.1:9224/page')
    with patch.object(client, '_connect_websocket') as connect, patch.object(
        client, '_send_text'), patch.object(client, '_receive_text', return_value=json.dumps({
            'id': 1, 'error': {'message': 'Target closed'},
        })):
        with pytest.raises(RuntimeError, match='Target closed'):
            with client.session(target) as session:
                session.command('Emulation.setGeolocationOverride', {})
        connect.return_value.__exit__.assert_called_once()
