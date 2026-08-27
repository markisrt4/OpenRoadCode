# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""HTTP transport for browser DeviceMotion reports owned by navigation service."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from controllers.navigation.browser_motion_adapter import BrowserMotionAdapter
from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf

_MAX_REQUEST_BYTES = 16_384
_MOTION_PAGE = b"""<!doctype html>
<meta name=viewport content='width=device-width,initial-scale=1'>
<title>OpenRoadCode Motion</title>
<body><h1>OpenRoadCode Motion</h1><button id=start>Start motion</button><pre id=status>Waiting to start.</pre>
<script>
const status=document.querySelector('#status');
let count=0, started=0, pending=false;
async function sendMotion(e){
  if(pending || !e.accelerationIncludingGravity || !e.rotationRate) return;
  pending=true; count++;
  const body={
    accelerationIncludingGravity:{x:e.accelerationIncludingGravity.x,y:e.accelerationIncludingGravity.y,z:e.accelerationIncludingGravity.z},
    rotationRate:{alpha:e.rotationRate.alpha,beta:e.rotationRate.beta,gamma:e.rotationRate.gamma},
    interval:e.interval,
    browserTimeMs:performance.now()
  };
  try {
    const r=await fetch('/motion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const elapsed=(performance.now()-started)/1000;
    status.textContent=r.ok?`events: ${count}\nrate: ${(count/elapsed).toFixed(1)} Hz\ninterval: ${e.interval} ms\n${JSON.stringify(body,null,2)}`:await r.text();
  } finally { pending=false; }
}
async function start(){
  if(typeof DeviceMotionEvent==='undefined'){status.textContent='DeviceMotionEvent is unavailable.';return;}
  if(typeof DeviceMotionEvent.requestPermission==='function'){
    const result=await DeviceMotionEvent.requestPermission();
    if(result!=='granted'){status.textContent='Motion permission denied.';return;}
  }
  count=0; started=performance.now();
  window.addEventListener('devicemotion',sendMotion);
  status.textContent='Listening for DeviceMotion events...';
}
document.querySelector('#start').onclick=()=>start().catch(e=>status.textContent=e.toString());
</script></body>"""


class BrowserMotionSource(NavigationSensorIf):
    """Receive browser DeviceMotion reports and expose fresh navigation samples."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8766,
        *,
        max_sample_age_seconds: float = 0.5,
    ) -> None:
        if max_sample_age_seconds <= 0.0:
            raise ValueError("max_sample_age_seconds must be greater than zero")
        self._host = host
        self._port = port
        self._max_sample_age_seconds = max_sample_age_seconds
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._latest: MotionSample | None = None
        self._latest_at: float | None = None
        self._sample_count = 0

    @property
    def is_connected(self) -> bool:
        return self._server is not None

    @property
    def port(self) -> int:
        return self._server.server_port if self._server is not None else self._port

    @property
    def url(self) -> str:
        host = "localhost" if self._host in {"127.0.0.1", "::1"} else self._host
        return f"http://{host}:{self.port}/"

    @property
    def sample_count(self) -> int:
        with self._lock:
            return self._sample_count

    @property
    def sample_age_ms(self) -> float | None:
        with self._lock:
            if self._latest_at is None:
                return None
            return (time.monotonic() - self._latest_at) * 1000.0

    def connect(self) -> None:
        if self._server is not None:
            return
        source = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path not in {"/", "/index.html"}:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(_MOTION_PAGE)

            def do_POST(self) -> None:
                if self.path != "/motion":
                    self.send_error(404)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= _MAX_REQUEST_BYTES:
                        raise ValueError("invalid request size")
                    sample = BrowserMotionAdapter.sample_from_payload(
                        json.loads(self.rfile.read(length))
                    )
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    self.send_error(400, str(exc))
                    return
                with source._lock:
                    source._latest = sample
                    source._latest_at = time.monotonic()
                    source._sample_count += 1
                self.send_response(204)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                pass

        self._server = ThreadingHTTPServer((self._host, self._port), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="navigation-browser-motion",
            daemon=True,
        )
        self._thread.start()
        print(f"[Motion] Open {self.url} and select 'Start motion'")

    def disconnect(self) -> None:
        server, thread = self._server, self._thread
        self._server = None
        self._thread = None
        with self._lock:
            self._latest = None
            self._latest_at = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def read_motion(self) -> MotionSample:
        with self._lock:
            if self._latest is None or self._latest_at is None:
                raise RuntimeError("No browser motion sample has been received yet")
            age = time.monotonic() - self._latest_at
            if age > self._max_sample_age_seconds:
                raise RuntimeError(
                    f"Browser motion sample is stale ({age * 1000.0:.0f} ms old)"
                )
            return self._latest
