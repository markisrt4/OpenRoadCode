# SPDX-License-Identifier: MIT
"""Background SDRForge ZMQ spectrum subscriber; never calls Tk directly."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Any

from .sdrforge_spectrum import SdrForgeSpectrumFrame
from .sdrforge_waterfall import SdrForgeWaterfall

_LOG = logging.getLogger(__name__)


def decode_spectrum_message(message: bytes) -> SdrForgeSpectrumFrame | None:
    """Decode SDRForge's 'topic {schema_version,payload}' PUB wire format."""
    topic, separator, encoded = message.partition(b" ")
    if separator != b" " or topic != b"spectrum":
        return None
    envelope = json.loads(encoded)
    if not isinstance(envelope, dict) or envelope.get("schema_version") != 1:
        raise ValueError("unsupported SDRForge telemetry envelope")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("invalid SDRForge spectrum payload")
    return SdrForgeSpectrumFrame.from_payload(payload)


@dataclass(frozen=True, slots=True)
class SdrForgeReceiverStatus:
    """Validated receiver state carried by SDRForge's receiver topic."""

    frequency_hz: int
    mode: str
    bandwidth_hz: int
    running: bool


def decode_receiver_message(message: bytes) -> SdrForgeReceiverStatus | None:
    """Decode mode-independent receiver metadata without interpreting WFM RDS."""
    topic, separator, encoded = message.partition(b" ")
    if separator != b" " or topic != b"receiver":
        return None
    envelope = json.loads(encoded)
    if not isinstance(envelope, dict) or envelope.get("schema_version") != 1:
        raise ValueError("unsupported SDRForge telemetry envelope")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("invalid SDRForge receiver payload")
    frequency = payload.get("channel_frequency_hz")
    mode = payload.get("mode")
    bandwidth = payload.get("bandwidth_hz")
    running = payload.get("running")
    # Legacy WFM publishers lack mode/bandwidth/running; ignore until upgraded.
    if mode is None or bandwidth is None or running is None:
        return None
    if (
        type(frequency) is not int
        or frequency <= 0
        or mode not in ("WFM", "NFM", "AM")
        or type(bandwidth) is not int
        or bandwidth <= 0
        or type(running) is not bool
    ):
        raise ValueError("invalid SDRForge receiver status")
    return SdrForgeReceiverStatus(frequency, mode, bandwidth, running)


class SdrForgeSpectrumSubscriber:
    """Read latest FFT and bounded history on a worker, not the GUI thread."""

    def __init__(
        self,
        *,
        endpoint: str = "tcp://127.0.0.1:5571",
        max_rows: int = 180,
        socket_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._factory = socket_factory
        self._history = SdrForgeWaterfall(max_rows)
        self._lock = Lock()
        self._receiver_status: SdrForgeReceiverStatus | None = None
        self._stop = Event()
        self._thread: Thread | None = None

    def snapshot(self) -> tuple[SdrForgeSpectrumFrame, ...]:
        """Safely copy the newest waterfall rows for a renderer."""
        with self._lock:
            return self._history.rows

    def latest_receiver_status(self) -> SdrForgeReceiverStatus | None:
        """Return the latest validated receiver mode and bandwidth."""
        with self._lock:
            return self._receiver_status

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="sdrforge-spectrum", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout_s)
            if thread.is_alive():
                raise RuntimeError("SDRForge spectrum subscriber did not stop")
        self._thread = None

    def _run(self) -> None:
        socket = None
        try:
            if self._factory is None:
                try:
                    import zmq
                except ImportError:
                    _LOG.warning("SDRForge spectrum requires pyzmq")
                    return
                socket = zmq.Context.instance().socket(zmq.SUB)
                socket.setsockopt(zmq.SUBSCRIBE, b"spectrum ")
                socket.setsockopt(zmq.SUBSCRIBE, b"receiver ")
                socket.setsockopt(zmq.RCVTIMEO, 200)
                socket.setsockopt(zmq.LINGER, 0)
                socket.connect(self._endpoint)
            else:
                socket = self._factory()
            while not self._stop.is_set():
                try:
                    message = socket.recv()
                except Exception as exc:
                    # pyzmq raises Again on receive timeout; injected sockets may
                    # use TimeoutError. Other transport failures terminate cleanly.
                    if isinstance(exc, TimeoutError) or type(exc).__name__ == "Again":
                        continue
                    _LOG.warning("SDRForge spectrum transport stopped: %s", exc)
                    return
                try:
                    frame = decode_spectrum_message(message)
                    receiver_status = decode_receiver_message(message)
                except (ValueError, TypeError, KeyError, UnicodeError) as exc:
                    _LOG.debug("Ignoring invalid SDRForge spectrum: %s", exc)
                    continue
                if frame is not None or receiver_status is not None:
                    with self._lock:
                        if frame is not None:
                            self._history.append(frame)
                        if receiver_status is not None:
                            self._receiver_status = receiver_status
        finally:
            if socket is not None:
                socket.close()
