# SPDX-License-Identifier: MIT
"""ZeroMQ adapter for SDRForge spectrum telemetry.

No Tk objects are touched from the subscriber thread. Newest spectrum wins.
"""
from __future__ import annotations

import json
import logging
import math
import threading
from queue import Empty, Queue
from typing import Any
from ui.radio.sdrforge_spectrum_if import SpectrumPresentation

LOG = logging.getLogger(__name__)


def spectrum_bins(topic: str, payload: dict[str, Any]) -> tuple[float, ...] | None:
    """Normalize libSDRForge power_db bins for a frontend-neutral snapshot."""
    if topic != "spectrum":
        return None
    raw = payload.get("power_db")
    if not isinstance(raw, list) or not raw:
        return None
    try:
        values = tuple(float(value) for value in raw)
    except (ValueError, TypeError):
        return None
    if not all(math.isfinite(value) for value in values):
        return None
    # dB magnitudes and normalized linear bins both occur in receiver APIs.
    if min(values) < 0 or max(values) > 1:
        floor, ceiling = min(values), max(values)
        span = max(ceiling - floor, 1e-9)
        return tuple((v - floor) / span for v in values)
    return values


class SdrForgeTelemetrySubscriber:
    """Bounded latest-only telemetry queue, safe to poll from the Tk thread."""

    def __init__(self, endpoint: str = "tcp://127.0.0.1:5571") -> None:
        self.endpoint = endpoint
        self._queue: Queue[SpectrumPresentation] = Queue(maxsize=1)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        if self._stop.is_set():
            raise RuntimeError("Closed SDRForge telemetry source cannot be restarted")
        self._thread = threading.Thread(target=self._run, name="orc-sdrforge-zmq", daemon=True)
        self._thread.start()

    def latest_spectrum(self) -> SpectrumPresentation | None:
        try:
            return self._queue.get_nowait()
        except Empty:
            return None

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)

    def _run(self) -> None:
        try:
            import zmq
        except ImportError:
            LOG.warning("SDRForge spectrum unavailable: install pyzmq")
            return
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        try:
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVHWM, 2)
            socket.setsockopt(zmq.SUBSCRIBE, b"spectrum ")
            socket.connect(self.endpoint)
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            while not self._stop.is_set():
                if not poller.poll(150):
                    continue
                try:
                    message = socket.recv(zmq.NOBLOCK)
                    topic, data = message.split(b" ", 1)
                    envelope = json.loads(data)
                    if envelope.get("schema_version") != 1:
                        continue
                    payload = envelope.get("payload")
                    if not isinstance(payload, dict):
                        continue
                    bins = spectrum_bins(topic.decode("ascii"), payload)
                    if bins is None:
                        continue
                    if self._queue.full():
                        try:
                            self._queue.get_nowait()
                        except Empty:
                            pass
                    self._queue.put_nowait(SpectrumPresentation(bins))
                except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                    LOG.debug("Ignoring malformed SDRForge telemetry", exc_info=True)
                except zmq.Again:
                    continue
        except zmq.ZMQError:
            if not self._stop.is_set():
                LOG.exception("SDRForge telemetry connection failed")
        finally:
            socket.close(0)
            context.term()
