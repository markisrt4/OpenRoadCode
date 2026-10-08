# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Own a local visualizer HTTP host and its embedded Chromium lifecycle."""
import os
from collections.abc import Callable
from pathlib import Path
from threading import Thread

from flask import Flask, send_from_directory
from werkzeug.serving import make_server

from apps.launchers.browser_launcher import BrowserKioskLauncher
from controllers.audio.music_analysis.music_analysis_session import MusicAnalysisSession
from frontends.web.audio_analysis.music_analysis_routes import create_music_analysis_routes
from frontends.web.audio_analysis.visualizer_page import VISUALIZER_HTML

WINDOW_CLASS = "openroadcode-music-visualizer"


class MusicVisualizerBrowser:
    """Application-selected host adapter consumed through BrowserMediaPlayerIf."""

    def __init__(self, session: MusicAnalysisSession, browser: BrowserKioskLauncher, *, color_scheme: Callable[[], str]) -> None:
        self._session = session
        self._browser = browser
        self._closed = False
        self._display = os.environ.get("DISPLAY", ":0")
        self._color_scheme = color_scheme
        app = Flask(__name__, static_folder=None)
        app.register_blueprint(create_music_analysis_routes(session))
        assets = Path(__file__).resolve().parents[3] / 'frontends' / 'web' / 'audio_analysis'

        @app.get('/')
        def page():
            scheme = "light" if self._color_scheme() == "light" else "dark"
            return VISUALIZER_HTML.replace('data-color-scheme="dark"', f'data-color-scheme="{scheme}"')

        @app.get('/web-assets/audio-analysis/<path:filename>')
        def asset(filename):
            if Path(filename).suffix not in {'.js', '.css'}:
                return '', 404
            return send_from_directory(assets, filename)

        self._server = make_server('127.0.0.1', 0, app, threaded=True)
        self.url = f'http://127.0.0.1:{self._server.server_port}/'
        self._thread = Thread(target=self._server.serve_forever, name='orc-visualizer-http', daemon=True)
        self._thread.start()

    def play(self, target: str, *, display: str, window_position=None, window_size=None) -> bool:
        if self._closed:
            raise RuntimeError('Visualizer host is closed')
        self.stop()
        self._display = display
        self._browser.set_preferred_color_scheme(self._color_scheme())
        self._browser.set_url(self.url)
        if window_position is not None and window_size is not None:
            self._browser.configure_app_window(position=window_position, size=window_size)
        self._browser.launch(display)
        return True

    def stop(self) -> None:
        try:
            self._browser.stop(self._display)
        finally:
            self._session.stop()

    def is_active(self) -> bool:
        return self._browser.is_running()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.stop()
        finally:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join(timeout=2)
