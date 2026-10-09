# SPDX-License-Identifier: MIT

from unittest.mock import Mock

import pytest

from controllers.radio.streaming_radio_artwork import ARTWORK_LIMIT_BYTES, download_station_artwork


def test_artwork_transport_enforces_payload_limit(monkeypatch):
    response = Mock()
    response.read.return_value = b"x" * (ARTWORK_LIMIT_BYTES + 1)
    connection = Mock()
    connection.__enter__ = Mock(return_value=response)
    connection.__exit__ = Mock(return_value=False)
    request = Mock(return_value=connection)
    monkeypatch.setattr("controllers.radio.streaming_radio_artwork.urlopen", request)
    with pytest.raises(ValueError, match="exceeds"):
        download_station_artwork("https://radio.test/logo")
    response.read.assert_called_once_with(ARTWORK_LIMIT_BYTES + 1)
    assert request.call_args.kwargs["timeout"] == 5.0


def test_artwork_transport_returns_encoded_bytes_without_toolkit_objects(monkeypatch):
    connection = Mock()
    response = Mock()
    response.read.return_value = b"encoded image"
    connection.__enter__ = Mock(return_value=response)
    connection.__exit__ = Mock(return_value=False)
    monkeypatch.setattr("controllers.radio.streaming_radio_artwork.urlopen", Mock(return_value=connection))
    assert download_station_artwork("https://radio.test/logo") == b"encoded image"
