# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bounded recovery of an SDR session after acquisition or startup failure."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, Protocol


class RadioSessionIf(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def process_once(self): ...


@dataclass(frozen=True)
class RadioRecoveryStatus:
    state: str
    reconnect_attempts: int
    successful_reconnects: int
    last_error: str | None
    last_cleanup_error: str | None


class RecoveringRadioSession:
    """Restart a session using a fresh source/audio instance on each attempt.

    The factory owns construction of a new session. Cleanup failures are
    recorded but do not mask the acquisition failure. A failed start is
    followed by stop() to release partially acquired resources.
    """

    def __init__(self, factory: Callable[[], RadioSessionIf], *,
                 max_retries: int = 5, retry_delay_seconds: float = 2.0,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        if max_retries < 0 or retry_delay_seconds < 0:
            raise ValueError("invalid recovery settings")
        self._factory = factory
        self._max_retries = max_retries
        self._delay = retry_delay_seconds
        self._sleep = sleep
        self._session: RadioSessionIf | None = None
        self._state = "DISCONNECTED"
        self._attempts = 0
        self._successes = 0
        self._last_error: str | None = None
        self._last_cleanup_error: str | None = None

    @property
    def session(self) -> RadioSessionIf | None:
        return self._session

    @property
    def status(self) -> RadioRecoveryStatus:
        return RadioRecoveryStatus(self._state, self._attempts, self._successes,
                                   self._last_error, self._last_cleanup_error)

    def start(self) -> None:
        if self._state == "CONNECTED":
            return
        self._connect(recovering=False)

    def process_once(self):
        if self._state != "CONNECTED" or self._session is None:
            raise RuntimeError("radio session is not connected")
        try:
            return self._session.process_once()
        except Exception as exc:
            self._last_error = str(exc)
            self._cleanup()
            self._connect(recovering=True)
            return None

    def stop(self) -> None:
        self._cleanup()
        self._state = "DISCONNECTED"

    def _cleanup(self) -> None:
        previous = self._session
        self._session = None
        if previous is not None:
            try:
                previous.stop()
            except Exception as exc:
                self._last_cleanup_error = str(exc)

    def _connect(self, *, recovering: bool) -> None:
        self._state = "RECONNECTING" if recovering else "CONNECTING"
        # Initial attempt plus configured retries, including failed startup.
        for index in range(self._max_retries + 1):
            if index:
                self._state = "RECONNECTING"
                self._sleep(self._delay)
            candidate = None
            try:
                candidate = self._factory()
                candidate.start()
            except Exception as exc:
                self._last_error = str(exc)
                if candidate is not None:
                    try:
                        candidate.stop()
                    except Exception as cleanup_exc:
                        self._last_cleanup_error = str(cleanup_exc)
                if index:
                    self._attempts += 1
                continue
            self._session = candidate
            if recovering or index:
                self._successes += 1
            self._attempts += index
            self._state = "CONNECTED"
            self._last_error = None
            return
        self._state = "FAILED"
        raise RuntimeError(
            f"SDR reconnection exhausted after {self._max_retries + 1} attempts: "
            f"{self._last_error}"
        )
