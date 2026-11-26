# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for local radar tile caching and presentation."""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import urlparse

import requests
from PIL import Image

from controllers.weather import RadarFrame, RadarPalette, RadarTileService
from controllers.weather.radar_tile_service import recolor_classic


def _png(pixel: tuple[int, int, int, int] = (0, 163, 224, 255)) -> bytes:
    image = Image.new("RGBA", (1, 1), pixel)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class _Response:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass


class _Session:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.calls: list[tuple[str, float]] = []
        self.closed = False
        self.adapter = Mock(spec=requests.Session, get=self.get, close=self.close)

    def get(self, url: str, *, timeout: float) -> _Response:
        self.calls.append((url, timeout))
        return _Response(self.content)

    def close(self) -> None:
        self.closed = True


def test_classic_recolor_maps_moderate_blue_to_green() -> None:
    result = recolor_classic(_png())
    with Image.open(BytesIO(result)) as image:
        pixel = image.convert("RGBA").getpixel((0, 0))
        assert isinstance(pixel, tuple) and len(pixel) == 4
        red, green, blue, alpha = pixel

    assert green > red
    assert green > blue
    assert alpha == 255


def test_service_caches_source_across_palettes(tmp_path: Path) -> None:
    session = _Session(_png())
    service = RadarTileService(cache_root=tmp_path, session=session.adapter)
    frame = RadarFrame(
        timestamp=200,
        tile_url="https://example.test/200/{z}/{x}/{y}.png",
        max_zoom=7,
    )
    try:
        path = urlparse(service.tile_url(frame, RadarPalette.UNIVERSAL)).path.format(
            z=7, x=34, y=47
        )
        universal = service._handle_path(path)
        classic = service._handle_path(path.replace("/universal/", "/classic/"))
    finally:
        service.close()

    assert universal == session.content
    assert classic != universal
    assert session.calls == [("https://example.test/200/7/34/47.png", 10.0)]


def test_readiness_waits_for_all_outstanding_tiles(tmp_path: Path) -> None:
    service = RadarTileService(cache_root=tmp_path, session=_Session(_png()).adapter)
    frame = RadarFrame(200, "https://example.test/{z}/{x}/{y}.png")
    try:
        service.tile_url(frame, RadarPalette.UNIVERSAL)
        key = service._frame_key(frame)
        assert not service.frame_ready(frame)
        service._begin_tile(key)
        service._begin_tile(key)
        service._finish_tile(key)
        assert not service.frame_ready(frame)
        service._finish_tile(key)
        assert service.frame_ready(frame)
        service._begin_tile(key)
        service._finish_tile(key, "bad GRIB")
        assert service.frame_error(frame) == "bad GRIB"
    finally:
        service.close()


def test_explicit_retry_clears_failed_frame_state(tmp_path: Path) -> None:
    service = RadarTileService(cache_root=tmp_path, session=_Session(_png()).adapter)
    frame = RadarFrame(200, "https://example.test/{z}/{x}/{y}.png")
    try:
        service.tile_url(frame, RadarPalette.UNIVERSAL)
        key = service._frame_key(frame)
        service._begin_tile(key)
        service._finish_tile(key, "temporary service failure")
        service.retry_frame(frame)
        assert service.frame_error(frame) is None
        assert not service.frame_ready(frame)
        service._begin_tile(key)
        service._finish_tile(key)
        assert service.frame_ready(frame)
    finally:
        service.close()


def test_success_of_other_tile_does_not_hide_failed_request(tmp_path: Path) -> None:
    service = RadarTileService(cache_root=tmp_path, session=_Session(_png()).adapter)
    frame = RadarFrame(200, "https://example.test/{z}/{x}/{y}.png")
    try:
        service.tile_url(frame, RadarPalette.UNIVERSAL)
        key = service._frame_key(frame)
        service._begin_tile(key)
        service._finish_tile(key, "offline", tile_id="failed")
        service._begin_tile(key)
        service._finish_tile(key, tile_id="other", has_echoes=False)
        assert service.frame_error(frame) == "offline"
        assert not service.frame_ready(frame)
        status = service.frame_status(frame)
        assert status.loaded == 1 and status.failed == 1
        service._begin_tile(key)
        service._finish_tile(key, tile_id="failed", has_echoes=True)
        assert service.frame_error(frame) is None
        assert service.frame_ready(frame)
        assert service.frame_status(frame).has_echoes is True
    finally:
        service.close()


def test_blank_png_is_loaded_but_failed_download_is_unavailable(tmp_path: Path) -> None:
    session = _Session(_png((0, 0, 0, 0)))
    service = RadarTileService(cache_root=tmp_path, session=session.adapter)
    frame = RadarFrame(200, "https://example.test/{z}/{x}/{y}.png")
    try:
        url = service.tile_url(frame, RadarPalette.UNIVERSAL).format(z=1, x=0, y=0)
        response = requests.get(url, timeout=2)
        assert response.status_code == 200
        status = service.frame_status(frame)
        assert status.loaded == 1 and status.failed == 0
        assert status.has_echoes is False and service.frame_ready(frame)
        session.content = b"not a PNG"
        failed_url = url.replace("/0/0.png", "/1/0.png")
        response = requests.get(failed_url, timeout=2)
        assert response.status_code == 502
        assert service.frame_status(frame).failed == 1
        assert not service.frame_ready(frame)
        session.content = _png()
        assert requests.get(f"{failed_url}?retry=1", timeout=2).status_code == 200
        status = service.frame_status(frame)
        assert (status.pending, status.loaded, status.failed) == (0, 2, 0)
        assert service.frame_ready(frame)
    finally:
        service.close()


def test_invalid_response_is_not_cached_and_corrupt_cache_recovers(tmp_path: Path) -> None:
    import pytest

    session = _Session(b"<html>bad upstream</html>")
    service = RadarTileService(cache_root=tmp_path, session=session.adapter)
    path = tmp_path / "tile.png"
    try:
        with pytest.raises(OSError):
            service._read_or_fetch(path, "https://example.test/tile.png")
        assert not path.exists()
        path.write_bytes(b"broken cache")
        session.content = _png()
        assert service._read_or_fetch(path, "https://example.test/tile.png") == _png()
        assert path.read_bytes() == _png()
    finally:
        service.close()


def test_retry_changes_tile_url_and_clears_failed_state(tmp_path: Path) -> None:
    service = RadarTileService(cache_root=tmp_path, session=_Session(_png()).adapter)
    frame = RadarFrame(200, "https://example.test/{z}/{x}/{y}.png")
    try:
        original = service.tile_url(frame, RadarPalette.UNIVERSAL)
        key = service._frame_key(frame)
        service._begin_tile(key)
        service._finish_tile(key, "offline", tile_id="failed")
        service.retry_frame(frame)
        retried = service.tile_url(frame, RadarPalette.UNIVERSAL)
        assert retried != original and "retry=1" in retried
        assert service.frame_status(frame).loaded == 0
        assert service.frame_error(frame) is None
    finally:
        service.close()
