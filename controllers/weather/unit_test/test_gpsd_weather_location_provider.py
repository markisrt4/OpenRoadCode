# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""GPSD reads must have timeouts and an overall fix deadline."""
import io
from unittest.mock import MagicMock, patch

import pytest

from controllers.weather.gpsd_weather_location_provider import GpsdWeatherLocationProvider


def test_reads_fix_after_gpsd_control_messages():
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.makefile.return_value = io.BytesIO(
        b'{"class":"VERSION"}\n'
        b'{"class":"TPV","mode":1}\n'
        b'{"class":"TPV","mode":3,"lat":42.8,"lon":-83.0}\n')
    with patch("controllers.weather.gpsd_weather_location_provider.socket.create_connection",
               return_value=connection) as connect:
        location = GpsdWeatherLocationProvider().get_location()
    assert location.latitude == 42.8
    assert location.longitude == -83.0
    assert location.source == "GPSD"
    connect.assert_called_once_with(("127.0.0.1", 2947), timeout=2.0)
    connection.sendall.assert_called_once_with(b'?WATCH={"enable":true,"json":true};\n')
    assert all(0 < call.args[0] <= 2.0 for call in connection.settimeout.call_args_list)


def test_control_messages_cannot_extend_fix_deadline():
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.makefile.return_value = io.BytesIO(b'{"class":"TPV","mode":1}\n')
    with patch("controllers.weather.gpsd_weather_location_provider.socket.create_connection",
               return_value=connection), patch(
                   "controllers.weather.gpsd_weather_location_provider.time.monotonic",
                   side_effect=(10.0, 10.5, 12.1)):
        with pytest.raises(TimeoutError, match="GPS lookup timed out"):
            GpsdWeatherLocationProvider().get_location()
    connection.settimeout.assert_called_once_with(1.5)
