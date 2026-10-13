# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Decode actual H.264/MPEG-TS over HTTP using a synthetic bridge fixture."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import shutil
import subprocess
import threading

import pytest

from hardware_io.camera.android_bridge_camera import AndroidBridgeCamera


def test_bridge_http_transport_decodes_real_h264_frames(tmp_path):
    cv2 = pytest.importorskip('cv2')
    if shutil.which('ffmpeg') is None or not cv2.videoio_registry.hasBackend(cv2.CAP_FFMPEG):
        pytest.skip('Integration check requires FFmpeg and OpenCV FFmpeg support')
    stream_path = tmp_path / 'fixture.ts'
    result = subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
        '-i', 'testsrc=size=160x90:rate=10', '-t', '3', '-pix_fmt', 'yuv420p',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
        '-f', 'mpegts', str(stream_path),
    ], capture_output=True, timeout=15)
    if result.returncode:
        pytest.skip('Synthetic H.264 fixture requires the FFmpeg libx264 encoder')
    video = stream_path.read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = (b'{"state":"streaming","codec":"h264","container":"mpegts"}'
                    if self.path == '/status' else video)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json' if self.path == '/status' else 'video/mp2t')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    camera = AndroidBridgeCamera(f'http://127.0.0.1:{server.server_port}')
    try:
        camera.open()
        first, second = camera.read(), camera.read()
        assert first.image.shape == (90, 160, 3)
        assert second.image.shape == (90, 160, 3)
        assert (first.sequence, second.sequence) == (0, 1)
        assert second.timestamp_s >= first.timestamp_s
    finally:
        camera.close()
        server.shutdown()
        server.server_close()
        thread.join(1)
