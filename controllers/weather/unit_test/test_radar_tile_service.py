# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for local radar tile caching and presentation."""

from io import BytesIO

from PIL import Image

from controllers.weather import RadarFrame, RadarPalette, RadarTileService
from controllers.weather.radar_tile_service import recolor_classic


def _png(pixel=(0, 163, 224, 255)) -> bytes:
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
        self.calls = []
        self.closed = False

    def get(self, url, *, timeout):
        self.calls.append((url, timeout))
        return _Response(self.content)

    def close(self):
        self.closed = True


def test_classic_recolor_maps_moderate_blue_to_green() -> None:
    result = recolor_classic(_png())
    with Image.open(BytesIO(result)) as image:
        red, green, blue, alpha = image.convert("RGBA").getpixel((0, 0))

    assert green > red
    assert green > blue
    assert alpha == 255


def test_service_caches_source_across_palettes(tmp_path) -> None:
    session = _Session(_png())
    service = RadarTileService(cache_root=tmp_path, session=session)
    frame = RadarFrame(
        timestamp=200,
        tile_url="https://example.test/200/{z}/{x}/{y}.png",
        max_zoom=7,
    )
    try:
        service.tile_url(frame, RadarPalette.UNIVERSAL)
        universal = service._handle_path("/radar/200/universal/7/34/47.png")
        classic = service._handle_path("/radar/200/classic/7/34/47.png")
    finally:
        service.close()

    assert universal == session.content
    assert classic != universal
    assert session.calls == [("https://example.test/200/7/34/47.png", 10.0)]
