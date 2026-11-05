# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Serialize short Waze gestures and cancel them when their view is hidden."""
import logging
from threading import Lock, Thread

from ui.navigation.waze_gesture_if import WazeGesture, WazeGestureState


class WazeGestureController:
    def __init__(self, adapter):
        self._adapter = adapter
        self._lock = Lock()
        self._visible = self._busy = self._closed = False
        self._generation = 0
        self._status = ''

    @property
    def state(self):
        with self._lock:
            return WazeGestureState(self._visible and not self._closed and self._adapter.available,
                                    self._busy, self._status)

    def set_visible(self, visible):
        with self._lock:
            self._visible = visible and not self._closed
            self._generation += 1
            self._status = ''

    def request_gesture(self, gesture):
        gesture = WazeGesture(gesture)
        with self._lock:
            if self._closed or self._busy or not self._visible or not self._adapter.available:
                return
            self._busy = True
            self._status = 'Sending gesture…'
            generation = self._generation
        Thread(target=self._perform, args=(gesture, generation), daemon=True).start()

    def _cancelled(self, generation):
        with self._lock:
            return self._closed or not self._visible or generation != self._generation

    def _perform(self, gesture, generation):
        status = gesture.value.replace('-', ' ').capitalize() + ' sent'
        try:
            self._adapter.perform(gesture, lambda: self._cancelled(generation))
        except Exception as error:
            logging.getLogger('navigation.waze.gestures').warning('Waze gesture failed: %s', error)
            status = 'Gesture unavailable. Keep Waze’s map visible and retry.'
        finally:
            with self._lock:
                self._busy = False
                if not self._closed and generation == self._generation:
                    self._status = status

    def close(self):
        with self._lock:
            self._closed = True
            self._visible = False
            self._generation += 1
            self._status = ''
