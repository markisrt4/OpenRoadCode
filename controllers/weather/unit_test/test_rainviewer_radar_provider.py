# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for RainViewer radar frame discovery."""

import pytest

from controllers.weather.providers import RainViewerRadarProvider


class _Response:
    def raise_for_status(self):
        pass

    def json(self):
        return {
            "host": "https://tilecache.rainviewer.com",
            "radar": {
                "past": [
                    {"time": 200, "path": "/v2/radar/200"},
                    {"time": 100, "path": "/v2/radar/100"},
                ]
            },
        }


class _Session:
    def get(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return _Response()


def test_frames_are_normalized_and_sorted():
    session = _Session()
    frames = RainViewerRadarProvider(session=session).get_frames()

    assert [frame.timestamp for frame in frames] == [100, 200]
    assert frames[-1].tile_url == (
        "https://tilecache.rainviewer.com/v2/radar/200/256/{z}/{x}/{y}/2/1_1.png"
    )
    assert frames[-1].max_zoom == 7
    assert session.args == (RainViewerRadarProvider.URL,)
    assert session.kwargs == {"timeout": 10.0}


def test_invalid_tile_size_is_rejected():
    with pytest.raises(ValueError, match="tile size"):
        RainViewerRadarProvider(tile_size=128)


def test_incomplete_metadata_is_rejected():
    class EmptyResponse(_Response):
        def json(self):
            return {"host": "https://tilecache.rainviewer.com", "radar": {"past": []}}

    class EmptySession(_Session):
        def get(self, *args, **kwargs):
            return EmptyResponse()

    with pytest.raises(ValueError, match="no usable radar frames"):
        RainViewerRadarProvider(session=EmptySession()).get_frames()
