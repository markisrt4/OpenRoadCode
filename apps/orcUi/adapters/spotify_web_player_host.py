# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Local host for a Spotify Web Playback SDK player instance."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from protocols.spotify import SpotifyAuth, SpotifyTokenStore, load_spotify_config_from_secrets
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8771
PLAYER_NAME = "OpenRoadCode"

_PLAYER_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>OpenRoadCode Spotify Player</title>
<style>
html,body{height:100%;margin:0;background:#05090d;color:#edf2f5;font-family:sans-serif}
body{display:grid;place-items:center}.card{text-align:center;padding:32px}.dot{width:18px;height:18px;border-radius:50%;background:#84ce1f;margin:0 auto 18px}
#status{font-size:22px;font-weight:700}.detail{color:#89959e;margin-top:8px}
</style></head><body><div class="card"><div class="dot"></div><div id="status">Starting Spotify player...</div><div id="detail" class="detail">Waiting for Spotify Web Playback SDK</div></div>
<script src="https://sdk.scdn.co/spotify-player.js"></script><script>
const status=document.getElementById('status'), detail=document.getElementById('detail');
async function token(){const r=await fetch('/token',{cache:'no-store'});if(!r.ok)throw new Error(await r.text());return (await r.json()).access_token;}
window.onSpotifyWebPlaybackSDKReady=async()=>{
  const player=new Spotify.Player({name:'OpenRoadCode',getOAuthToken:async cb=>{try{cb(await token())}catch(e){status.textContent='Spotify authentication failed';detail.textContent=e.message}},volume:0.5,enableMediaSession:true});
  player.addListener('ready',({device_id})=>{status.textContent='OpenRoadCode is ready';detail.textContent='Spotify Connect device: '+device_id;fetch('/ready',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id})});});
  player.addListener('not_ready',({device_id})=>{status.textContent='Spotify player offline';detail.textContent=device_id||'';});
  for(const name of ['initialization_error','authentication_error','account_error','playback_error']) player.addListener(name,({message})=>{status.textContent=name.replaceAll('_',' ');detail.textContent=message;fetch('/error',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,message})});});
  const connected=await player.connect();if(!connected){status.textContent='Spotify player did not connect';detail.textContent='Web Playback SDK connect() returned false';}
};
</script></body></html>"""


class SpotifyWebPlayerHost:
    """Serve the SDK page and provide it short-lived OAuth access tokens."""

    def __init__(self, *, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        manager = EnvironmentVariableSecretManager()
        config = load_spotify_config_from_secrets(manager)
        if config is None:
            raise RuntimeError("Spotify is not configured; SPOTIFY_CLIENT_ID is required")
        self._auth = SpotifyAuth(config=config, token_store=SpotifyTokenStore())
        self._host = host
        self._port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._device_id: str | None = None
        self._error: str | None = None
        self._lock = threading.Lock()

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}/"

    @property
    def device_id(self) -> str | None:
        with self._lock:
            return self._device_id

    @property
    def error(self) -> str | None:
        with self._lock:
            return self._error

    def start(self) -> None:
        if self._server is not None:
            return
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/" or self.path.startswith("/?"):
                    self._send(200, "text/html; charset=utf-8", _PLAYER_HTML.encode())
                    return
                if self.path == "/token":
                    try:
                        access_token = owner._auth.get_access_token()
                    except Exception as error:
                        owner._set_error(str(error)); self._send(500, "text/plain; charset=utf-8", str(error).encode()); return
                    payload = json.dumps({"access_token": access_token}).encode()
                    self._send(200, "application/json", payload)
                    return
                self._send(404, "text/plain; charset=utf-8", b"Not found")

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0")); raw = self.rfile.read(length)
                try: payload = json.loads(raw or b"{}")
                except json.JSONDecodeError: payload = {}
                if self.path == "/ready":
                    device_id = payload.get("device_id")
                    if isinstance(device_id, str) and device_id: owner._set_device_id(device_id)
                    self._send(204, "text/plain", b""); return
                if self.path == "/error":
                    owner._set_error(f"{payload.get('name','Spotify error')}: {payload.get('message','')}")
                    self._send(204, "text/plain", b""); return
                self._send(404, "text/plain; charset=utf-8", b"Not found")

            def _send(self, status: int, content_type: str, body: bytes) -> None:
                self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers()
                if body: self.wfile.write(body)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        self._server = ThreadingHTTPServer((self._host, self._port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="orcui-spotify-web-player", daemon=True)
        self._thread.start()

    def close(self) -> None:
        server = self._server; self._server = None
        if server is not None: server.shutdown(); server.server_close()
        thread = self._thread; self._thread = None
        if thread is not None and thread.is_alive(): thread.join(timeout=1.0)

    def _set_device_id(self, device_id: str) -> None:
        with self._lock: self._device_id = device_id; self._error = None
        print(f"[Spotify Player] ready device_id={device_id}")

    def _set_error(self, message: str) -> None:
        with self._lock: self._error = message
        print(f"WARNING: Spotify Web Player: {message}")
