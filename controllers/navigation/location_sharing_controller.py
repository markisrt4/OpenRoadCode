# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Freshness and visibility policy for optional host-to-Android location sharing."""
import math
from threading import Event, Lock, Thread
import time

from ui.navigation.location_sharing_if import AndroidLocationProviderIf, LocationSnapshot


class LocationSharingController:
    def __init__(self, provider: AndroidLocationProviderIf | None, *, status, clock=time.time,
                 android_requested=False):
        self._provider, self._status, self._clock = provider, status, clock
        self._snapshot = LocationSnapshot()
        self._active = False
        self._navigation_active = False
        self._generation = 0
        self._lock = Lock()
        self._stop = Event()
        self._thread = None
        self._last_status = None
        self._android_requested = android_requested

    def start(self):
        if self._thread is None:
            self._thread = Thread(target=self._run, name='android-location-sharing', daemon=True)
            self._thread.start()

    def update_snapshot(self, snapshot: LocationSnapshot):
        with self._lock:
            self._snapshot = snapshot

    def set_active(self, active: bool):
        with self._lock:
            self._active = active
            self._generation += 1

    def _run(self):
        try:
            while not self._stop.wait(1):
                self._tick()
        finally:
            self._clear()

    def set_navigation_active(self, active: bool):
        """A retained Waze session needs GPS even while another screen is shown."""
        with self._lock:
            self._navigation_active = active
            self._generation += 1

    def _clear(self):
        if self._provider is not None:
            try:
                self._provider.clear_location()
            except (OSError, RuntimeError):
                pass

    def _tick(self):
        with self._lock:
            snapshot, active, generation = self._snapshot, self._active or self._navigation_active, self._generation
        simulated = 'simulat' in snapshot.source.casefold()
        age = self._clock() - snapshot.sampled_at_s if snapshot.sampled_at_s is not None else float('inf')
        point = snapshot.point
        fresh = (not snapshot.is_cached and not simulated and point is not None
                 and math.isfinite(age) and -5 <= age <= 10
                 and math.isfinite(point.latitude_rad) and abs(point.latitude_rad) <= math.pi / 2
                 and math.isfinite(point.longitude_rad) and abs(point.longitude_rad) <= math.pi)
        if snapshot.is_cached:
            location_status = 'Last known location (cached) — waiting for a live fix.'
        elif simulated:
            location_status = 'Simulated location — not shared with Android.'
        elif fresh:
            source = 'Android Bridge' if snapshot.source.startswith('android-') else 'Browser' if snapshot.source == 'browser' else 'GPS'
            location_status = f'Live location · {source}'
        elif point is not None:
            location_status = 'Location expired — waiting for a fresh fix.'
        else:
            location_status = 'Waiting for a live location.'
        android_status = '' if self._provider is None and not self._android_requested else (
            'Android location sharing is not configured.' if self._provider is None else 'Android sharing paused.')
        if self._provider is not None:
            with self._lock:
                current = generation == self._generation and not self._stop.is_set()
            if active and fresh and current:
                accuracy = snapshot.accuracy_m
                accuracy = accuracy if accuracy is not None and math.isfinite(accuracy) and accuracy > 0 else 50.0
                try:
                    self._provider.send_location(point, accuracy)
                    android_status = 'Sharing live location with Android.'
                except (OSError, RuntimeError):
                    self._clear()
                    android_status = 'Android location sharing failed. Check the device connection and location setup.'
                with self._lock:
                    still_active = generation == self._generation and not self._stop.is_set()
                if not still_active:
                    self._clear()
                    android_status = 'Android sharing paused.'
            else:
                self._clear()
                if active:
                    android_status = 'Android is waiting for a fresh live location.'
        value = (location_status, android_status)
        if value != self._last_status and not self._stop.is_set():
            self._last_status = value
            self._status(*value)

    def close(self):
        self.set_active(False)
        self.set_navigation_active(False)
        self._stop.set()
