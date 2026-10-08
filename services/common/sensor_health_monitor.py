# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Observe validated sensor telemetry without opening or competing for sensors."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from messaging.contracts.navigation.position_state_validator import validate_position_state
from messaging.contracts.navigation.imu_state_validator import validate_imu_state
from messaging.contracts.navigation.magnetic_field_state_validator import validate_magnetic_field_state
from messaging.contracts.navigation.attitude_state_validator import validate_attitude_state
from messaging.contracts.environmental.ambient_light_state_validator import validate_ambient_light_state
from messaging.contracts.environmental.barometric_state_validator import validate_barometric_state
from ui.system_diagnostics import SensorHealthSnapshot

# A quiet, disabled, or unconfigured topic is unknown, not failed hardware.
SENSORS = {
    "openroad.navigation.position": ("GPS position", validate_position_state, 10.0),
    "openroad.navigation.imu": ("IMU", validate_imu_state, 3.0),
    "openroad.navigation.magnetic_field": ("Magnetometer", validate_magnetic_field_state, 5.0),
    "openroad.navigation.attitude": ("Attitude (derived)", validate_attitude_state, 5.0),
    "openroad.environmental.ambient_light": ("Ambient light", validate_ambient_light_state, 30.0),
    "openroad.environmental.barometric": ("Barometer", validate_barometric_state, 10.0),
}


@dataclass
class _Observation:
    received: float | None = None
    advanced: float | None = None
    timestamp: tuple[int, int] | None = None
    invalid: int = 0
    invalid_last: bool = False
    detail: str = ""
    arrivals: deque[float] = field(default_factory=lambda: deque(maxlen=1024))


class SensorHealthMonitor:
    """Own one receiver thread and bounded per-topic, per-source observations."""

    def __init__(self, *, subscriber_factory: Callable | None = None, monotonic=time.monotonic) -> None:
        self._factory = subscriber_factory or _subscriber
        self._monotonic = monotonic
        self._lock = threading.Lock()
        self._observations: dict[tuple[str, str], _Observation] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._subscriber = None
        self._status = "not_started"

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    def start(self) -> None:
        if self._thread is not None:
            return
        try:
            self._subscriber = self._factory()
            for topic in SENSORS:
                self._subscriber.subscribe(topic)
        except Exception as error:
            if self._subscriber is not None:
                self._subscriber.close()
            with self._lock:
                self._status = ("unavailable: pyzmq is missing from this Python environment"
                                if isinstance(error, ModuleNotFoundError) and error.name == "zmq"
                                else f"unavailable ({type(error).__name__})")
            return
        self._stop.clear()
        with self._lock:
            self._status = "listening"
        self._thread = threading.Thread(target=self._run, name="orc-sensor-health", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._subscriber is not None:
            self._subscriber.close()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        with self._lock:
            self._status = "stopped"

    def observe(self, topic: str, payload: Mapping[str, Any]) -> None:
        """Record validity and timestamp advancement using monotonic receipt time."""
        definition = SENSORS.get(topic)
        if definition is None:
            return
        source = payload.get("source")
        source = source[:96] if isinstance(source, str) else "unknown"
        invalid = False
        try:
            definition[1](payload)
            timestamp = (payload["timestamp"]["seconds"], payload["timestamp"]["nanoseconds"])
        except (ValueError, TypeError, KeyError):
            invalid = True
            timestamp = None
        now = self._monotonic()
        with self._lock:
            key = (topic, source)
            if key not in self._observations and len(self._observations) >= 48:
                oldest = min(self._observations, key=lambda key: self._observations[key].received or 0)
                self._observations.pop(oldest)
            observed = self._observations.setdefault(key, _Observation())
            observed.received = now
            observed.invalid_last = invalid
            if invalid:
                observed.invalid += 1
                return
            observed.arrivals.append(now)
            observed.detail = ""
            if observed.timestamp is None or timestamp > observed.timestamp:
                observed.advanced = now
                observed.timestamp = timestamp
            elif timestamp < observed.timestamp:
                observed.detail = "Source timestamp moved backward; waiting for timestamp recovery"
            if topic == "openroad.navigation.attitude" and all(value is None for value in payload["data"].values()):
                observed.detail = "No usable attitude estimates"
            if topic == "openroad.navigation.position":
                data = payload["data"]
                if data["is_cached"]:
                    observed.detail = "Cached position; not a live GPS fix"
                elif data["fix_mode"] not in (2, 3) or data["latitude_rad"] is None or data["longitude_rad"] is None:
                    observed.detail = "No valid GPS fix"

    def snapshots(self) -> tuple[SensorHealthSnapshot, ...]:
        now = self._monotonic()
        rows = []
        with self._lock:
            for topic, (name, _, timeout) in SENSORS.items():
                matches = [(source, observation) for (observed_topic, source), observation in self._observations.items() if observed_topic == topic]
                if not matches:
                    rows.append(SensorHealthSnapshot(name=name, topic=topic, stale_after_seconds=timeout))
                    continue
                for source, observation in sorted(matches):
                    received_age = now - observation.received if observation.received is not None else None
                    advanced_age = now - observation.advanced if observation.advanced is not None else None
                    arrivals = [value for value in observation.arrivals if value >= now - 5]
                    rate = ((len(arrivals) - 1) / (arrivals[-1] - arrivals[0]) if len(arrivals) >= 2 and arrivals[-1] > arrivals[0]
                            else 0.0 if not arrivals else None)
                    state, detail = "streaming", "Validated telemetry with advancing sample timestamps"
                    if received_age is not None and received_age > timeout:
                        state, detail = "stale", "No recent telemetry"
                    elif observation.invalid_last:
                        state, detail = "invalid", "Latest message failed contract validation"
                    elif advanced_age is None or advanced_age > timeout:
                        state, detail = "stale", "Sample timestamp stopped advancing"
                    elif observation.detail:
                        state, detail = "degraded", observation.detail
                    rows.append(SensorHealthSnapshot(
                        name=name, topic=topic, source=source, state=state, detail=detail,
                        last_received_age_seconds=received_age, last_sample_age_seconds=advanced_age,
                        message_rate_hz=rate, invalid_message_count=observation.invalid,
                        stale_after_seconds=timeout,
                    ))
        return tuple(rows)

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    topic, payload = self._subscriber.receive()
                    self.observe(topic, payload)
                except (ValueError, TypeError):
                    # A malformed transport payload has no validated topic identity.
                    continue
                except Exception as error:
                    if not self._stop.is_set():
                        with self._lock:
                            self._status = f"unavailable ({type(error).__name__})"
                    break
        finally:
            self._subscriber.close()


def _subscriber():
    # The service-manager's resource accounting remains usable without optional pyzmq.
    from messaging.zeromq.subscriber import ZeroMqSubscriber
    return ZeroMqSubscriber()
