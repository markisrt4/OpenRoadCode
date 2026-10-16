# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Supply fresh ORC fixes to a visible Waze browser through local CDP."""
from __future__ import annotations

import logging
import math
from threading import Event, Lock, Thread
import time
from urllib.parse import urlsplit

from protocols.chromium.chromium_devtools_client import ChromiumDevToolsClient
from ui.media.browser_player_if import BrowserMediaPlayerIf
from ui.navigation import GeoPoint

LOGGER = logging.getLogger(__name__)
WAZE_DEVTOOLS_PORT = 9224
WAZE_HOSTS = frozenset({'embed.waze.com', 'www.waze.com', 'waze.com'})


class WazeLocationPlayer:
    """Own the GPS connection for exactly one managed browser lifetime."""

    def __init__(self, player: BrowserMediaPlayerIf, *, client=None, clock=time.monotonic):
        self._player = player
        self._client = client or ChromiumDevToolsClient(port=WAZE_DEVTOOLS_PORT)
        self._clock = clock
        self._lock = Lock()
        self._position: GeoPoint | None = None
        self._received_at = 0.0
        self._stop = Event()
        self._thread: Thread | None = None
        self._closed = False

    def update_position(self, point: GeoPoint | None) -> None:
        """Accept live SI fixes; None immediately invalidates the previous fix."""
        with self._lock:
            if self._closed:
                return
            if point is not None and (
                not math.isfinite(point.latitude_rad) or not math.isfinite(point.longitude_rad)
                or abs(point.latitude_rad) > math.pi / 2 or abs(point.longitude_rad) > math.pi
            ):
                point = None
            self._position = point
            self._received_at = self._clock()

    def play(self, target: str, *, display: str, window_position=None, window_size=None) -> bool:
        self.stop()
        if self._closed:
            return False
        opened = self._player.play(target, display=display,
            window_position=window_position, window_size=window_size)
        if opened:
            self._stop = Event()
            self._thread = Thread(target=self._run, args=(self._stop,),
                                  name='waze-location', daemon=True)
            self._thread.start()
        return opened

    def stop(self) -> None:
        """Wait for in-flight local commands before stopping/replacing the browser."""
        self._stop.set()
        worker, self._thread = self._thread, None
        try:
            if worker is not None:
                worker.join()
        finally:
            self._player.stop()

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._position = None
        self.stop()

    def _params(self) -> dict[str, float]:
        with self._lock:
            point = self._position
            if point is None or self._clock() - self._received_at > 10.0:
                # Empty params explicitly report position unavailable, rather than
                # presenting a cached/default location as the current GPS fix.
                return {}
            params = {'latitude': math.degrees(point.latitude_rad),
                      'longitude': math.degrees(point.longitude_rad), 'accuracy': 50.0}
            if point.altitude_m is not None and math.isfinite(point.altitude_m):
                params['altitude'] = point.altitude_m
            return params

    def _run(self, stop: Event) -> None:
        reported = False
        while not stop.is_set():
            try:
                target = next((target for target in self._client.targets()
                    if urlsplit(target.url).scheme == 'https'
                    and urlsplit(target.url).hostname in WAZE_HOSTS), None)
                if target is not None and not stop.is_set():
                    with self._client.session(target) as session:
                        if stop.is_set():
                            return
                        origin = 'https://' + urlsplit(target.url).netloc
                        session.command('Browser.grantPermissions', {
                            'origin': origin, 'permissions': ['geolocation'],
                        })
                        while not stop.is_set():
                            current = self._client.targets()
                            if stop.is_set() or not any(
                                page.id == target.id and page.url == target.url for page in current
                            ):
                                break
                            session.command('Emulation.setGeolocationOverride', self._params())
                            reported = False
                            if stop.wait(1.0):
                                return
            except (OSError, ValueError, RuntimeError) as error:
                if not stop.is_set() and not reported:
                    LOGGER.warning('Waze location connection unavailable: %s', error)
                    reported = True
            if stop.wait(1.0):
                return
