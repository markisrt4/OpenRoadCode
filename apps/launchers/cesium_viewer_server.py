"""Loopback transport adapter for local viewer assets and semantic close requests."""

from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import base64
import mimetypes
from pathlib import Path
import secrets
import threading
from urllib.parse import unquote, urlsplit

from apps.launchers.cesium_sdk import require_sdk
from apps.launchers.local_terrain_pack import LocalTerrainCatalog
from apps.launchers.local_statewide_detail import PagedTerrainCatalog
from ui.navigation.cesium_viewer_state import CesiumViewerState
from ui.navigation.boundary_overlay_state import BoundaryOverlayState
from ui.navigation.local_imagery_state import LocalImageryStackState
import sqlite3
from tools.map_builder.builder.validate import ValidationError

_WEB = Path(__file__).resolve().parents[2] / "frontends/web/cesium"
_WORLD_LAND = Path(__file__).resolve().parents[2] / "resources/maps/world_land.geojson"
_WORLD_LAKES = Path(__file__).resolve().parents[2] / "resources/maps/world_lakes.geojson"


class CesiumViewerServer:
    """Own the local origin, immutable view state, and bounded serving lifecycle."""

    def __init__(self, sdk: Path, state: CesiumViewerState, *, imagery=None, imagery_layers=(), terrain=None, buildings=None, tiles=None, roads=None, boundaries=None, imagery_pyramids=()):
        self._sdk = require_sdk(sdk)
        self._state = state
        self._imagery_pyramids = tuple(imagery_pyramids)
        if len(self._imagery_pyramids) > 8:
            raise ValueError("At most eight offline imagery pyramids may be mounted")
        self._imagery = imagery
        self._imagery_layers = tuple(imagery_layers)
        self._imagery_stack = LocalImageryStackState(tuple(pack.state for pack in self._imagery_layers))
        self._terrain = terrain
        self._buildings = buildings
        self._tiles = tiles
        self._roads = roads
        if boundaries is not None and not isinstance(boundaries, BoundaryOverlayState):
            raise TypeError('Viewer boundaries must use the presentation contract')
        self._boundaries = boundaries
        self._token = secrets.token_urlsafe(32)
        self.close_requested = threading.Event()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Handler, owner=self))
        self._server.daemon_threads = True
        self._thread = None
        self._closed = False

    @property
    def url(self):
        return f"http://127.0.0.1:{self._server.server_port}/"

    def start(self):
        if self._closed or self._thread is not None:
            raise RuntimeError("Viewer server is closed or already started")
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="orc-cesium-http", daemon=True)
        self._thread.start()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._thread is not None:
            self._server.shutdown()
            self._thread.join(timeout=3)
            self._thread = None
        self._server.server_close()


class _Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, owner, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)

    def log_message(self, *_args):
        pass

    def _trusted_host(self):
        return self.headers.get("Host") == urlsplit(self.owner.url).netloc

    def do_GET(self):
        if not self._trusted_host():
            self.send_error(403)
            return
        path = unquote(urlsplit(self.path).path)
        if path == "/config.json":
            document = self.owner._state.document()
            document["close_token"] = self.owner._token
            document['roads_available'] = self.owner._roads is not None
            document['roads_max_zoom'] = self.owner._roads.max_zoom if self.owner._roads is not None else 14
            if self.owner._boundaries is not None:
                document['boundary_overlay'] = self.owner._boundaries.document()
            document['imagery_pyramids'] = [pack.state.document() for pack in self.owner._imagery_pyramids]
            for index, layer in enumerate(document['imagery_pyramids']):
                layer['url'] = f'/data/imagery-detail/{index}/{{z}}/{{x}}/{{y}}'
            if self.owner._imagery_layers:
                document['imagery_layers'] = self.owner._imagery_stack.document()
                for index, layer in enumerate(document['imagery_layers']):
                    layer['url'] = f'/data/imagery/{index}'
            if self.owner._imagery is not None:
                document["imagery"] = self.owner._imagery.state.document()
                document["imagery"]["url"] = "/data/imagery.jpg"
            if self.owner._terrain is not None:
                if isinstance(self.owner._terrain, LocalTerrainCatalog):
                    document["terrain"] = self.owner._terrain.state.document()
                    for index, tile in enumerate(document["terrain"]["tiles"]):
                        tile["url"] = f"/data/terrain/{index}"
                else:
                    document["terrain"] = self.owner._terrain.document()
            if self.owner._buildings is not None:
                document["buildings"] = self.owner._buildings.document()
            if self.owner._tiles is not None:
                document["map_tiles"] = self.owner._tiles.state.document()
            self._send(json.dumps(document).encode(), "application/json")
            return
        if path == "/data/world-land.geojson":
            self._send(_WORLD_LAND.read_bytes(), "application/geo+json")
            return
        if path == "/data/world-lakes.geojson":
            self._send(_WORLD_LAKES.read_bytes(), "application/geo+json")
            return
        if path.startswith('/data/terrain-page/') and isinstance(self.owner._terrain,PagedTerrainCatalog):
            try:
                parts=path.removeprefix('/data/terrain-page/').split('/')
                if len(parts)!=3 or any(not p.isascii() or not p.isdigit() or len(p)>6 for p in parts):
                    raise ValueError('Invalid terrain page address')
                document=self.owner._terrain.page(*(int(p) for p in parts))
                self._send(json.dumps(document).encode(),'application/json')
            except (ValueError,OSError,KeyError):self.send_error(404)
            return
        if path.startswith('/data/terrain-chunk/') and isinstance(self.owner._terrain,PagedTerrainCatalog):
            try:self._send(self.owner._terrain.chunk(path.removeprefix('/data/terrain-chunk/')),'application/json')
            except (ValueError,OSError,KeyError):self.send_error(404)
            return
        if path.startswith('/data/terrain/') and isinstance(self.owner._terrain, LocalTerrainCatalog):
            index = path.removeprefix('/data/terrain/')
            if (not index.isascii() or not index.isdigit() or len(index) > 4
                    or int(index) >= len(self.owner._terrain.payloads)):
                self.send_error(404)
                return
            self._send(self.owner._terrain.payloads[int(index)].read_bytes(), 'application/json')
            return
        if path.startswith('/data/roads/') and self.owner._roads is not None:
            try:
                parts=path.removeprefix('/data/roads/').split('/')
                if len(parts)!=3 or any(not part.isascii() or not part.isdigit() or len(part)>6 for part in parts):
                    raise ValueError('Invalid road tile URL')
                state=self.owner._roads.tile(*(int(part) for part in parts))
                self._send(json.dumps(state.document()).encode(),'application/json')
            except (ValueError,ValidationError,sqlite3.Error,OSError):
                self.send_error(404,'Offline road tile unavailable')
            return
        if path.startswith('/data/imagery-detail/'):
            try:
                parts = path.removeprefix('/data/imagery-detail/').split('/')
                if len(parts) != 4 or any(not p.isascii() or not p.isdigit() or len(p)>6 for p in parts):
                    raise ValueError('Invalid imagery tile URL')
                index, zoom, x, y = map(int, parts)
                if index >= len(self.owner._imagery_pyramids):
                    raise ValueError('Unknown imagery pyramid')
                pack = self.owner._imagery_pyramids[index]
                content = pack.tile(zoom,x,y)
                if content is None:
                    # Valid address with no source coverage: show the underlying
                    # overview instead of repeated tile errors or fabricated data.
                    content = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=')
                    self._send(content,'image/png')
                else:
                    self._send(content,'image/jpeg' if pack.state.image_format in ('jpg','jpeg') else 'image/'+pack.state.image_format)
            except (ValueError,OSError,sqlite3.Error):
                self.send_error(404,'Offline imagery tile unavailable')
            return
        if path.startswith('/data/imagery/'):
            index = path.removeprefix('/data/imagery/')
            if not index.isascii() or not index.isdigit() or len(index) > 2 or int(index) >= len(self.owner._imagery_layers):
                self.send_error(404)
                return
            image = self.owner._imagery_layers[int(index)].image
            self._send(image.read_bytes(), mimetypes.guess_type(image.name)[0] or 'application/octet-stream')
            return
        if path == "/data/imagery.jpg" and self.owner._imagery is not None:
            content_type = mimetypes.guess_type(self.owner._imagery.image.name)[0] or 'application/octet-stream'
            self._send(self.owner._imagery.image.read_bytes(), content_type)
            return
        if path.startswith('/data/tiles/') and self.owner._tiles is not None:
            parts = path.removeprefix('/data/tiles/').split('/')
            candidate = self.owner._tiles.files.get(parts[0], {}).get(parts[1]) if len(parts) == 2 else None
            if candidate is None:
                self.send_error(404)
            else:
                content_type = 'image/jpeg' if parts[1] == 'imagery.jpg' else 'application/json'
                self._send(candidate.read_bytes(),content_type)
            return
        if path.startswith("/sdk/"):
            root, relative = self.owner._sdk, path.removeprefix("/sdk/")
        else:
            root, relative = _WEB, "index.html" if path == "/" else path.lstrip("/")
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self._send(candidate.read_bytes(), content_type)

    def do_POST(self):
        if (not self._trusted_host() or self.path != "/close"
                or not secrets.compare_digest(self.headers.get("X-ORC-Token", ""), self.owner._token)):
            self.send_error(403)
            return
        self._send(b"{}", "application/json")
        self.owner.close_requested.set()

    def _send(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Closing a browser may cancel SDK/worker asset requests.
            pass
