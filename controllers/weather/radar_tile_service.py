# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Cache and locally serve provider radar tiles with optional recoloring."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse

import requests
from PIL import Image

from common.xdg_paths import openroadcode_cache_dir
from controllers.weather.radar_palette import RadarPalette
from controllers.weather.radar_provider_if import RadarFrame


# Representative points from RainViewer's published Universal Blue dBZ table.
# The classic output follows the familiar NEXRAD-style intensity progression.
_UNIVERSAL_DBZ = (
    (0, (130, 123, 105)), (5, (146, 136, 113)), (10, (206, 192, 135)),
    (15, (136, 221, 238)), (20, (0, 163, 224)), (25, (0, 119, 170)),
    (30, (0, 85, 136)), (35, (255, 238, 0)), (40, (255, 170, 0)),
    (45, (255, 68, 0)), (50, (193, 0, 0)), (55, (255, 170, 255)),
    (60, (255, 119, 255)), (65, (255, 255, 255)),
)


def _classic_color(dbz: int, alpha: int) -> tuple[int, int, int, int]:
    if dbz < 5:
        return 0, 0, 0, 0
    if dbz < 20:
        return 0, 236, 0, alpha
    if dbz < 30:
        return 0, 200, 0, alpha
    if dbz < 35:
        return 0, 145, 0, alpha
    if dbz < 40:
        return 255, 255, 0, alpha
    if dbz < 45:
        return 255, 165, 0, alpha
    if dbz < 50:
        return 255, 0, 0, alpha
    if dbz < 55:
        return 190, 0, 0, alpha
    if dbz < 60:
        return 255, 0, 255, alpha
    if dbz < 65:
        return 160, 0, 200, alpha
    return 255, 255, 255, alpha


def _nearest_dbz(red: int, green: int, blue: int) -> int:
    return min(
        _UNIVERSAL_DBZ,
        key=lambda item: (
            (red - item[1][0]) ** 2
            + (green - item[1][1]) ** 2
            + (blue - item[1][2]) ** 2
        ),
    )[0]


def recolor_classic(source: bytes) -> bytes:
    """Translate a Universal Blue PNG into an ORC classic radar palette."""
    with Image.open(BytesIO(source)) as image:
        rgba = image.convert("RGBA")
        pixels = []
        for red, green, blue, alpha in rgba.get_flattened_data():
            if alpha == 0:
                pixels.append((red, green, blue, alpha))
            else:
                pixels.append(_classic_color(_nearest_dbz(red, green, blue), alpha))
        rgba.putdata(pixels)
        output = BytesIO()
        rgba.save(output, format="PNG", optimize=True)
        return output.getvalue()


class RadarTileService:
    """Proxy/cache radar XYZ tiles behind a stable localhost endpoint."""

    def __init__(
        self,
        *,
        cache_root: str | Path | None = None,
        session: requests.Session | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._cache_root = Path(cache_root) if cache_root else openroadcode_cache_dir("radar")
        self._session = session or requests.Session()
        self._timeout_seconds = timeout_seconds
        self._frames: dict[int, str] = {}

        service = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                try:
                    data = service._handle_path(self.path)
                except (OSError, ValueError, requests.RequestException) as error:
                    self.send_error(502, str(error))
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "public, max-age=3600")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    # MapLibre can cancel in-flight tiles after pan/zoom/style changes.
                    return

            def log_message(self, format: str, *args) -> None:
                del format, args

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = Thread(target=self._server.serve_forever, name="radar-tile-service", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=1.0)
        self._session.close()

    def tile_url(self, frame: RadarFrame, palette: RadarPalette) -> str:
        self._frames[frame.timestamp] = frame.tile_url
        port = self._server.server_address[1]
        return (
            f"http://127.0.0.1:{port}/radar/{frame.timestamp}/{palette.value}"
            "/{z}/{x}/{y}.png"
        )

    def _handle_path(self, raw_path: str) -> bytes:
        parts = urlparse(raw_path).path.strip("/").split("/")
        if len(parts) != 6 or parts[0] != "radar" or not parts[5].endswith(".png"):
            raise ValueError("invalid radar tile path")
        timestamp = int(parts[1])
        palette = RadarPalette(parts[2])
        z, x = int(parts[3]), int(parts[4])
        y = int(parts[5].removesuffix(".png"))
        template = self._frames.get(timestamp)
        if template is None:
            raise ValueError("unknown radar frame")

        source_path = self._cache_root / str(timestamp) / "source" / str(z) / str(x) / f"{y}.png"
        source = self._read_or_fetch(source_path, template.format(z=z, x=x, y=y))
        if palette is RadarPalette.UNIVERSAL:
            return source

        derived_path = self._cache_root / str(timestamp) / palette.value / str(z) / str(x) / f"{y}.png"
        if derived_path.is_file():
            return derived_path.read_bytes()
        derived = recolor_classic(source)
        self._write_cache(derived_path, derived)
        return derived

    def _read_or_fetch(self, path: Path, url: str) -> bytes:
        if path.is_file():
            return path.read_bytes()
        response = self._session.get(url, timeout=self._timeout_seconds)
        response.raise_for_status()
        data = response.content
        self._write_cache(path, data)
        return data

    @staticmethod
    def _write_cache(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
