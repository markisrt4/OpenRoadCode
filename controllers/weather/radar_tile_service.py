# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Cache and locally serve provider radar tiles with optional recoloring."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse
import logging

import requests
from PIL import Image, ImageDraw

from common.xdg_paths import openroadcode_cache_dir
from controllers.weather.radar_palette import RadarPalette
from controllers.weather.radar_tile_status import RadarTileStatus
from controllers.weather.radar_provider_if import RadarFrame
from controllers.weather.hrrr_tiles import HrrrTileSource, color_hrrr_reflectivity
from controllers.weather.weather_logging import WeatherLog
from common.logging.structured import event, operation

LOGGER = logging.getLogger("weather.radar.tiles")


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
        self._hrrr_tiles = HrrrTileSource(self._cache_root / "hrrr-models", self._session)
        self._frames: dict[str, str] = {}
        self._load_lock = Lock()
        self._pending: dict[str, int] = {}
        self._loaded: set[str] = set()
        self._errors: dict[str, str] = {}
        self._tile_errors: dict[str, dict[str, str]] = {}
        self._tile_echoes: dict[str, dict[str, bool | None]] = {}
        self._retries: dict[str, int] = {}
        self._cache_locks_guard = Lock()
        self._cache_locks: dict[Path, Lock] = {}
        self._log = WeatherLog("weather.radar.tiles")

        service = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                key = urlparse(self.path).path.strip("/").split("/")[1:2]
                key = key[0] if key else ""
                tile_id = urlparse(self.path).path
                service._begin_tile(key)
                operation_id = service._log.requested()
                try:
                    with operation(operation_id):
                        data = service._handle_path(self.path)
                        echoes = service._png_has_echoes(data)
                        service._log.succeeded(stage="tile")
                except (OSError, ValueError, RuntimeError, requests.RequestException) as error:
                    service._log.failed(error, operation_id, stage="tile")
                    service._finish_tile(key, str(error), tile_id=tile_id)
                    try:
                        self.send_error(502, str(error))
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    return
                service._finish_tile(key, tile_id=tile_id, has_echoes=echoes)
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
        self._log.emit(logging.INFO, "tiles.started", "Local weather tile service started")

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=1.0)
        self._session.close()
        self._log.emit(logging.INFO, "tiles.stopped", "Local weather tile service stopped")

    def tile_url(self, frame: RadarFrame, palette: RadarPalette) -> str:
        key = self._frame_key(frame)
        self._frames[key] = frame.tile_url
        port = self._server.server_address[1]
        template = f"http://127.0.0.1:{port}/radar/{key}/{palette.value}/{{z}}/{{x}}/{{y}}.png"
        with self._load_lock:
            retry = self._retries.get(key, 0)
        return template + (f"?retry={retry}" if retry else "")

    @staticmethod
    def _frame_key(frame: RadarFrame) -> str:
        return f"{frame.timestamp}-{sha256(frame.tile_url.encode()).hexdigest()[:16]}"

    def _begin_tile(self, key: str) -> None:
        with self._load_lock:
            if key in self._frames:
                self._pending[key] = self._pending.get(key, 0) + 1

    def _finish_tile(self, key: str, error: str | None = None, *,
                     tile_id: str = "", has_echoes: bool | None = None) -> None:
        with self._load_lock:
            if key not in self._frames:
                return
            self._pending[key] = max(0, self._pending.get(key, 0) - 1)
            failures = self._tile_errors.setdefault(key, {})
            echoes = self._tile_echoes.setdefault(key, {})
            if error is not None:
                failures[tile_id] = error
                echoes.pop(tile_id, None)
            else:
                self._loaded.add(key)
                echoes[tile_id] = has_echoes
                failures.pop(tile_id, None)
            if failures:
                self._errors[key] = next(iter(failures.values()))
            else:
                self._errors.pop(key, None)

    def frame_status(self, frame: RadarFrame) -> RadarTileStatus:
        """Summarize successful/failed requests without treating missing data as clear weather."""
        key = self._frame_key(frame)
        with self._load_lock:
            echoes = self._tile_echoes.get(key, {})
            visible = (True if any(value is True for value in echoes.values()) else
                       False if echoes and all(value is False for value in echoes.values()) else None)
            return RadarTileStatus(self._pending.get(key, 0), len(echoes),
                                   len(self._tile_errors.get(key, {})), visible)

    @staticmethod
    def _png_has_echoes(data: bytes) -> bool:
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG":
                raise ValueError("radar tile is not a PNG image")
            return image.convert("RGBA").getchannel("A").getbbox() is not None

    def retry_frame(self, frame: RadarFrame) -> None:
        """Clear a previous processing error before an explicit frame retry."""
        with self._load_lock:
            key = self._frame_key(frame)
            if self._errors.pop(key, None) is not None:
                self._loaded.discard(key)
                self._tile_errors.pop(key, None)
                self._tile_echoes.pop(key, None)
                self._retries[key] = self._retries.get(key, 0) + 1

    def frame_ready(self, frame: RadarFrame) -> bool:
        """Report at least one successful tile and no outstanding tile work."""
        key = self._frame_key(frame)
        with self._load_lock:
            return key in self._loaded and not self._pending.get(key, 0) and key not in self._errors

    def frame_error(self, frame: RadarFrame) -> str | None:
        """Return the last reported tile-generation failure for a frame."""
        with self._load_lock:
            return self._errors.get(self._frame_key(frame))

    def _handle_path(self, raw_path: str) -> bytes:
        parts = urlparse(raw_path).path.strip("/").split("/")
        if len(parts) != 6 or parts[0] != "radar" or not parts[5].endswith(".png"):
            raise ValueError("invalid radar tile path")
        key = parts[1]
        if not all(character in "0123456789abcdef-" for character in key):
            raise ValueError("invalid radar frame key")
        palette = RadarPalette(parts[2])
        z, x = int(parts[3]), int(parts[4])
        y = int(parts[5].removesuffix(".png"))
        template = self._frames.get(key)
        if template is None:
            raise ValueError("unknown radar frame")

        source_path = self._cache_root / key / "source" / str(z) / str(x) / f"{y}.png"
        source_url = template.format(z=z, x=x, y=y)
        if source_url.startswith("orc-injected://"):
            source = self._synthetic_tile(source_url, z, x, y, palette)
        elif source_url.startswith("orc-hrrr-layer://"):
            from controllers.weather.hrrr_map_layers import color_model_layer
            with self._cache_lock(source_path):
                cached = self._cached_png(source_path)
                if cached is not None:
                    return cached
                params = parse_qs(urlparse(template).query)
                kind = params.get("kind", [""])[0]
                second = params.get("secondary", [None])[0]
                source = color_model_layer(self._hrrr_tiles.tile(template, z, x, y), kind,
                                          self._hrrr_tiles.tile(second, z, x, y) if second else None)
                self._write_cache(source_path, source)
                return source
        elif source_url.startswith("orc-hrrr://"):
            with self._cache_lock(source_path):
                cached = self._cached_png(source_path)
                if cached is not None:
                    source = cached
                else:
                    source = color_hrrr_reflectivity(self._hrrr_tiles.tile(template, z, x, y), _UNIVERSAL_DBZ)
                    self._write_cache(source_path, source)
        else:
            source = self._read_or_fetch(source_path, source_url)
        if palette is RadarPalette.UNIVERSAL:
            return source

        derived_path = self._cache_root / key / palette.value / str(z) / str(x) / f"{y}.png"
        lock = self._cache_lock(derived_path)
        with lock:
            cached = self._cached_png(derived_path)
            if cached is not None:
                return cached
            derived = recolor_classic(source)
            self._write_cache(derived_path, derived)
            return derived

    @staticmethod
    def _synthetic_tile(
        url: str, z: int, x: int, y: int, palette: RadarPalette
    ) -> bytes:
        """Render a deterministic transparent radar tile for an injected scenario."""
        parsed = urlparse(url)
        scenario = parsed.netloc
        try:
            frame_index = int(parsed.path.strip("/").split("/")[0])
        except (ValueError, IndexError) as exc:
            raise ValueError("invalid injected radar tile URL") from exc
        if scenario not in {"clear", "storm", "severe"}:
            raise ValueError(f"unsupported injected radar scenario: {scenario}")

        image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        if scenario != "clear":
            draw = ImageDraw.Draw(image, "RGBA")
            seed = (x * 37 + y * 53 + z * 19 + frame_index * 31) % 256
            center_x = (72 + seed + frame_index * 18) % 320 - 32
            center_y = (96 + (seed * 3) % 128) % 256
            colors = (
                ((0, 145, 0, 150), (255, 255, 0, 180), (255, 0, 0, 205), (255, 0, 255, 230))
                if palette is RadarPalette.CLASSIC
                else ((0, 85, 136, 150), (0, 119, 170, 180), (0, 163, 224, 205), (136, 221, 238, 230))
            )
            if scenario == "storm":
                cells = (
                    (center_x, center_y, ((82, colors[0]), (58, colors[1]), (36, colors[2]))),
                )
            else:
                # Severe weather is intentionally broader and multi-cell so it is
                # visually distinct from the ordinary storm scenario at map scale.
                cells = (
                    (
                        center_x,
                        center_y,
                        ((105, colors[0]), (78, colors[1]), (52, colors[2]), (27, colors[3])),
                    ),
                    (
                        center_x + 92,
                        center_y - 54,
                        ((70, colors[0]), (48, colors[1]), (29, colors[2]), (14, colors[3])),
                    ),
                    (
                        center_x - 76,
                        center_y + 66,
                        ((58, colors[0]), (38, colors[1]), (21, colors[2])),
                    ),
                )
            for cell_x, cell_y, rings in cells:
                for radius, color in rings:
                    draw.ellipse(
                        (
                            cell_x - radius,
                            cell_y - radius,
                            cell_x + radius,
                            cell_y + radius,
                        ),
                        fill=color,
                    )
        output = BytesIO()
        image.save(output, format="PNG", optimize=True)
        return output.getvalue()

    def _cache_lock(self, path: Path) -> Lock:
        with self._cache_locks_guard:
            return self._cache_locks.setdefault(path, Lock())

    def _read_or_fetch(self, path: Path, url: str) -> bytes:
        # A corrupt/HTML response must never become a permanent "empty radar" cache hit.
        with self._cache_lock(path):
            cached = self._cached_png(path)
            if cached is not None:
                return cached
            operation_id = self._log.requested()
            try:
                response = self._session.get(url, timeout=self._timeout_seconds)
                response.raise_for_status()
                data = response.content
                self._png_has_echoes(data)
                self._write_cache(path, data)
            except Exception as error:
                self._log.failed(error, operation_id, stage="download")
                raise
            self._log.succeeded(operation_id, stage="download", byte_count=len(data))
            return data

    @classmethod
    def _cached_png(cls, path: Path) -> bytes | None:
        if not path.is_file():
            event(LOGGER, logging.DEBUG, "tiles.cache_miss", "Weather tile cache miss")
            return None
        data = path.read_bytes()
        try:
            cls._png_has_echoes(data)
            event(LOGGER, logging.DEBUG, "tiles.cache_hit", "Weather tile cache hit")
            return data
        except (OSError, ValueError):
            # No path, XYZ coordinate, frame key, or corrupt content is retained.
            event(LOGGER, logging.DEBUG,
                  "tiles.cache_invalid", "Invalid weather tile cache entry discarded")
            path.unlink(missing_ok=True)
            return None

    @staticmethod
    def _write_cache(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
