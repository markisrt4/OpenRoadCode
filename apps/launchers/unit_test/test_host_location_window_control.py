# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import http.client
from unittest.mock import Mock
from apps.launchers.host_location_window_control import HostLocationWindowControl


def test_close_control_accepts_only_the_local_permission_page_and_only_hides():
    hide = Mock(return_value=True)
    control = HostLocationWindowControl(origins={'http://127.0.0.1:8765'}, hide=hide, port=0)
    try:
        for origin, expected in [('https://example.com', 403), ('http://127.0.0.1:8765', 204)]:
            connection = http.client.HTTPConnection('127.0.0.1', control.port)
            connection.request('POST', '/hide', headers={'Origin': origin})
            response = connection.getresponse()
            assert response.status == expected
            response.read()
            connection.close()
        hide.assert_called_once_with()
    finally:
        control.close()
