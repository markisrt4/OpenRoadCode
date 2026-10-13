"""Loopback transport adapter for local viewer assets and semantic close requests."""

from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import threading
from urllib.parse import unquote, urlsplit

from apps.launchers.cesium_sdk import require_sdk
from ui.navigation.cesium_viewer_state import CesiumViewerState
from ui.navigation.local_imagery_state import LocalImageryStackState
import sqlite3
from tools.map_builder.builder.validate import ValidationError

_WEB = Path(__file__).resolve().parents[2] / "frontends/web/cesium"


class CesiumViewerServer:
    """Own the local origin, immutable view state, and bounded serving lifecycle."""

    def __init__(self, sdk: Path, state: CesiumViewerState, *, imagery=None, imagery_layers=(), terrain=None, buildings=None, tiles=None):
        self._sdk = require_sdk(sdk)
        self._state = state
        self._imagery = imagery
        self._imagery_layers = tuple(imagery_layers)
        self._imagery_stack = LocalImageryStackState(tuple(pack.state for pack in self._imagery_layers))
        self._terrain = terrain
        self._buildings = buildings
        self._tiles = tiles
        # Disabled while isolating Termux:X11 crashes introduced by the overlay.
        # Keep the base terrain/imagery/building viewer available.
        self._roads = None
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
            if self.owner._imagery_layers:
                document['imagery_layers'] = self.owner._imagery_stack.document()
                for index, layer in enumerate(document['imagery_layers']):
                    layer['url'] = f'/data/imagery/{index}'
            if self.owner._imagery is not None:
                document["imagery"] = self.owner._imagery.state.document()
                document["imagery"]["url"] = "/data/imagery.jpg"
            if self.owner._terrain is not None:
                document["terrain"] = self.owner._terrain.document()
            if self.owner._buildings is not None:
                document["buildings"] = self.owner._buildings.document()
            if self.owner._tiles is not None:
                document["map_tiles"] = self.owner._tiles.state.document()
            self._send(json.dumps(document).encode(), "application/json")
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
        if path.startswith('/data/imagery/'):
            index = path.removeprefix('/data/imagery/')
            if not index.isascii() or not index.isdigit() or len(index) > 1 or int(index) >= len(self.owner._imagery_layers):
                self.send_error(404)
                return
            image = self.owner._imagery_layers[int(index)].image
            self._send(image.read_bytes(), 'image/png' if image.suffix == '.png' else 'image/jpeg')
            return
        if path == "/data/imagery.jpg" and self.owner._imagery is not None:
            content_type = 'image/png' if self.owner._imagery.image.suffix == '.png' else 'image/jpeg'
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
