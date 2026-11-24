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
from ui.radio.rf_radio_if import RadioTelemetry

LOG = logging.getLogger(__name__)


def spectrum_bins(topic: str, payload: dict[str, Any]) -> tuple[float, ...] | None:
    """Normalize libSDRForge power_db bins for a frontend-neutral snapshot."""
    if topic != "spectrum":
        return None
    raw = payload.get("power_db")
    if not isinstance(raw, list) or not raw:
        return None
    try:
        finite_values = tuple(float(value) for value in raw if value is not None)
    except (ValueError, TypeError):
        return None
    if not finite_values or not all(math.isfinite(value) for value in finite_values):
        return None
    # SDRForge serializes nonfinite FFT bins as null. Preserve the row by
    # replacing those bins with its measured noise floor, not by dropping it.
    floor_value = min(finite_values)
    values = tuple(floor_value if value is None else float(value) for value in raw)
    # dB magnitudes and normalized linear bins both occur in receiver APIs.
    if min(values) < 0 or max(values) > 1:
        floor, ceiling = min(values), max(values)
        span = max(ceiling - floor, 1e-9)
        return tuple((v - floor) / span for v in values)
    return values


def receiver_telemetry(topic: str, payload: dict[str, Any]) -> RadioTelemetry | None:
    """Map the SDRForge receiver snapshot to ORC's existing radio contract."""
    if topic != "receiver":
        return None
    frequency = payload.get("channel_frequency_hz")
    if not isinstance(frequency, (int, float)) or isinstance(frequency, bool):
        return None
    if not math.isfinite(frequency) or frequency <= 0:
        return None
    rds = payload.get("rds")
    if rds is not None and not isinstance(rds, dict):
        return None
    rds = rds or {}
    name = rds.get("program_service") or rds.get("ps") or ""
    radio_text = rds.get("radio_text") or rds.get("rt") or ""
    if not isinstance(name, str) or not isinstance(radio_text, str):
        return None
    name = name.strip()[:64]
    radio_text = radio_text.strip()[:256]
    stereo = payload.get("stereo_locked")
    if stereo is not None and not isinstance(stereo, bool):
        return None
    mode = payload.get("mode")
    bandwidth = payload.get("bandwidth_hz")
    running = payload.get("running")
    # Older SDRForge builds do not provide these optional status fields.
    if mode is not None and mode not in ("WFM", "NFM", "AM"):
        return None
    if bandwidth is not None and (type(bandwidth) is not int or bandwidth <= 0):
        return None
    if running is not None and type(running) is not bool:
        return None
    return RadioTelemetry(
        frequency_hz=int(frequency),
        rds=radio_text or name,
        station_name=name,
        radio_text=radio_text,
        stereo_locked=stereo,
        mode=mode,
        bandwidth_hz=bandwidth,
        receiver_running=running,
    )


class ReceiverSequenceFilter:
    """Reject reordered receiver messages within a publisher lifetime."""

    def __init__(self) -> None:
        self._stream_id: str | None = None
        self._sequence = -1
        self._retired_streams: set[str] = set()

    def accept(self, payload: dict[str, Any]) -> bool:
        """Accept legacy payloads and strictly increasing sequenced updates."""
        stream_id = payload.get("stream_id")
        sequence = payload.get("sequence")
        if stream_id is None and sequence is None:
            # Legacy publisher: no ordering information available.
            return True
        if (
            not isinstance(stream_id, str)
            or not stream_id
            or type(sequence) is not int
            or sequence < 1
        ):
            return False
        if stream_id in self._retired_streams:
            return False
        if stream_id != self._stream_id:
            if self._stream_id is not None:
                self._retired_streams.add(self._stream_id)
            self._stream_id = stream_id
            self._sequence = -1
        if sequence <= self._sequence:
            return False
        self._sequence = sequence
        return True


class SdrForgeTelemetrySubscriber:
    """Bounded latest-only telemetry queue, safe to poll from the Tk thread."""

    def __init__(self, endpoint: str = "tcp://127.0.0.1:5571") -> None:
        self.endpoint = endpoint
        self._queue: Queue[SpectrumPresentation] = Queue(maxsize=1)
        self._receiver_queue: Queue[RadioTelemetry] = Queue(maxsize=1)
        self._receiver_order = ReceiverSequenceFilter()
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

    def latest_receiver(self) -> RadioTelemetry | None:
        try:
            return self._receiver_queue.get_nowait()
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
            socket.setsockopt(zmq.SUBSCRIBE, b"receiver ")
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
                    topic_name = topic.decode("ascii")
                    if topic_name == "receiver":
                        receiver = receiver_telemetry(topic_name, payload)
                        if receiver is not None and self._receiver_order.accept(payload):
                            if self._receiver_queue.full():
                                self._receiver_queue.get_nowait()
                            self._receiver_queue.put_nowait(receiver)
                        continue
                    bins = spectrum_bins(topic_name, payload)
                    if bins is None:
                        continue
                    if self._queue.full():
                        try:
                            self._queue.get_nowait()
                        except Empty:
                            pass
                    center = payload.get("center_frequency_hz")
                    rate = payload.get("sample_rate_hz")
                    center = center if type(center) is int and center > 0 else None
                    rate = rate if type(rate) is int and rate > 0 else None
                    raw_power = payload.get("power_db")
                    power_db = None
                    if isinstance(raw_power, list) and len(raw_power) == len(bins):
                        try:
                            finite = tuple(float(value) for value in raw_power if value is not None)
                            if finite and all(math.isfinite(value) for value in finite):
                                noise_floor = min(finite)
                                power_db = tuple(
                                    noise_floor if value is None else float(value)
                                    for value in raw_power
                                )
                        except (TypeError, ValueError):
                            pass
                    self._queue.put_nowait(
                        SpectrumPresentation(
                            bins,
                            center_frequency_hz=center,
                            sample_rate_hz=rate,
                            power_db=power_db,
                        )
                    )
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
