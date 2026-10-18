# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Supply fresh ORC fixes to a visible Waze browser through local CDP."""
from __future__ import annotations

from collections.abc import Callable
import logging
import math
from threading import Event, Lock, Thread
import time
from urllib.parse import urlsplit

from protocols.chromium.chromium_devtools_client import ChromiumDevToolsClient
from ui.media.browser_player_if import BrowserMediaPlayerIf, BrowserThemeRequestHandlerIf
from ui.navigation import GeoPoint

LOGGER = logging.getLogger(__name__)
WAZE_DEVTOOLS_PORT = 9224
WAZE_HOSTS = frozenset({'embed.waze.com', 'www.waze.com', 'waze.com'})


class WazeLocationPlayer(BrowserThemeRequestHandlerIf):
    """Own the GPS connection for exactly one managed browser lifetime."""

    def __init__(self, player: BrowserMediaPlayerIf, *, client=None, clock=time.monotonic,
                 preferred_color_scheme: Callable[[], str] | None = None):
        self._preferred_color_scheme = preferred_color_scheme
        self._theme_dirty = Event()
        self._player = player
        self._client = client or ChromiumDevToolsClient(port=WAZE_DEVTOOLS_PORT)
        self._clock = clock
        self._lock = Lock()
        self._position: GeoPoint | None = None
        self._received_at = 0.0
        self._stop = Event()
        self._thread: Thread | None = None
        self._closed = False

    def request_theme_refresh(self) -> None:
        if not self._closed:
            self._theme_dirty.set()

    def _apply_theme(self, session, previous: str | None, stop: Event) -> str | None:
        if self._preferred_color_scheme is None or stop.is_set():
            return previous
        scheme = self._preferred_color_scheme()
        if scheme not in ('dark', 'light'):
            return previous
        dirty = self._theme_dirty.is_set()
        self._theme_dirty.clear()
        if scheme == previous and not dirty:
            return previous
        for method, params in (
            ('Emulation.setEmulatedMedia', {'features': [
                {'name': 'prefers-color-scheme', 'value': scheme},
            ]}),
            ('Emulation.setAutoDarkModeOverride', {'enabled': scheme == 'dark'}),
        ):
            if stop.is_set():
                break
            try:
                session.command(method, params)
            except RuntimeError:
                # Older Chromium may not implement experimental auto-dark.
                # Keep GPS and the remaining theme controls working.
                LOGGER.warning('Waze browser does not support theme command %s', method)
        return scheme

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
        parsed = urlsplit(target)
        bootstrap = parsed.scheme == 'https' and parsed.hostname in WAZE_HOSTS
        # Start the owned page before Waze can cache a denied permission result.
        opened = self._player.play('about:blank' if bootstrap else target, display=display,
            window_position=window_position, window_size=window_size)
        if opened and bootstrap:
            self._stop = Event()
            self._thread = Thread(target=self._run, args=(self._stop, target if bootstrap else None),
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

    def _run(self, stop: Event, initial_url: str | None = None) -> None:
        reported = False
        while not stop.is_set():
            try:
                target = next((target for target in self._client.targets()
                    if (target.url == 'about:blank' if initial_url is not None else
                        urlsplit(target.url).scheme == 'https'
                        and urlsplit(target.url).hostname in WAZE_HOSTS)), None)
                if target is not None and not stop.is_set():
                    with self._client.session(target) as session:
                        if stop.is_set():
                            return
                        applied_theme = self._apply_theme(session, None, stop)
                        if stop.is_set():
                            return
                        destination = initial_url or target.url
                        parsed = urlsplit(destination)
                        origin = parsed.scheme + '://' + parsed.netloc
                        # Install the provider before granting access, since a
                        # permission-change listener can immediately request GPS.
                        session.command('Emulation.setGeolocationOverride', self._params())
                        if stop.is_set():
                            return
                        session.command('Browser.grantPermissions', {
                            'origin': origin, 'permissions': ['geolocation'],
                        })
                        navigating = initial_url is not None
                        if navigating:
                            if stop.is_set():
                                return
                            result = session.command('Page.navigate', {'url': destination})
                            if result.get('errorText'):
                                raise RuntimeError('Could not load the Waze page')
                            initial_url = None
                        while not stop.is_set():
                            page = next((page for page in self._client.targets()
                                         if page.id == target.id), None)
                            if stop.is_set() or page is None:
                                break
                            parsed = urlsplit(page.url)
                            current_origin = parsed.scheme + '://' + parsed.netloc
                            if page.url not in ('', 'about:blank') and current_origin != origin:
                                # Retain this session across route/query changes
                                # and Chromium's empty URL during navigation.
                                # A confirmed different origin releases the grant.
                                break
                            applied_theme = self._apply_theme(session, applied_theme, stop)
                            if stop.is_set():
                                return
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
