# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own a vehicle-state source and publish automotive telemetry."""

from __future__ import annotations

from dataclasses import replace
import logging
import threading
import time

from common.logging.structured import current_operation, event, operation

from controllers.automotive.gear_estimator import GearEstimator
from controllers.automotive.vehicle_state_source_if import VehicleStateSourceIf
from messaging.contracts.automotive import VehicleStatePublisher
from protocols.obd2 import Obd2Error

LOGGER = logging.getLogger("automotive.runtime")


class AutomotiveRuntime:
    """Publish complete vehicle-state snapshots at a configured rate."""

    def __init__(
        self,
        source: VehicleStateSourceIf,
        publisher,
        *,
        publish_source: str = "automotive-service",
        rate_hz: float = 10.0,
        reconnect_interval_s: float = 2.0,
        gear_estimator: GearEstimator | None = None,
    ) -> None:
        if rate_hz <= 0.0:
            raise ValueError("rate_hz must be greater than zero")
        if reconnect_interval_s <= 0.0:
            raise ValueError("reconnect_interval_s must be greater than zero")
        self._source = source
        self._state_publisher = VehicleStatePublisher(publisher, source=publish_source)
        self._period_s = 1.0 / rate_hz
        self._reconnect_interval_s = reconnect_interval_s
        self._gear_estimator = gear_estimator
        self._stop_event = threading.Event()
        self._connected = False
        self._connection_failed = False
        self._running = False

    def start(self) -> None:
        """Prepare the runtime; source connection is managed by run()."""
        self._stop_event.clear()

    def run(self) -> None:
        """Publish snapshots and reconnect the source after OBD-II failures."""
        self.start()
        self._running = True
        event(
            LOGGER,
            logging.INFO,
            "service.started",
            "Automotive publishing started",
            rate_hz=1.0 / self._period_s,
        )
        try:
            while not self._stop_event.is_set():
                if not self._connected:
                    if not self._try_connect():
                        self._stop_event.wait(self._reconnect_interval_s)
                        continue

                started = time.monotonic()
                try:
                    state = self._source.read_state()
                except Obd2Error as exc:
                    self._connection_failed = True
                    event(
                        LOGGER,
                        logging.WARNING,
                        "source.lost",
                        "Automotive source lost",
                        exception_type=type(exc).__name__,
                    )
                    self._disconnect_source()
                    self._stop_event.wait(self._reconnect_interval_s)
                    continue

                if self._gear_estimator is not None:
                    state = replace(
                        state,
                        transmission_gear=self._gear_estimator.estimate(
                            state.engine_speed_rad_s,
                            state.vehicle_speed_m_s,
                        ),
                    )
                self._state_publisher.publish(state)
                event(LOGGER, logging.DEBUG, "state.published", "Vehicle snapshot published")
                remaining = self._period_s - (time.monotonic() - started)
                if remaining > 0.0:
                    self._stop_event.wait(remaining)
        except Exception as exc:
            event(
                LOGGER,
                logging.ERROR,
                "service.failed",
                "Automotive publishing failed",
                exception_type=type(exc).__name__,
            )
            raise
        finally:
            self.close()

    def close(self) -> None:
        """Stop publishing and disconnect the owned source."""
        self._stop_event.set()
        try:
            self._disconnect_source()
        finally:
            if self._running:
                self._running = False
                event(LOGGER, logging.INFO, "service.stopped", "Automotive publishing stopped")

    def _try_connect(self) -> bool:
        with operation(current_operation()):
            return self._connect_source()

    def _connect_source(self) -> bool:
        event(LOGGER, logging.DEBUG, "source.connecting", "Connecting automotive source")
        try:
            self._source.connect()
        except Obd2Error as exc:
            if not self._connection_failed:
                event(
                    LOGGER,
                    logging.WARNING,
                    "source.unavailable",
                    "Automotive source unavailable",
                    exception_type=type(exc).__name__,
                )
            self._connection_failed = True
            self._disconnect_source()
            return False
        self._connected = True
        event(
            LOGGER,
            logging.INFO,
            "source.connected",
            "Automotive source connected",
            recovered=self._connection_failed,
        )
        self._connection_failed = False
        return True

    def _disconnect_source(self) -> None:
        if not self._connected:
            return
        try:
            self._source.disconnect()
        except Exception as exc:
            event(
                LOGGER,
                logging.ERROR,
                "source.disconnect_failed",
                "Automotive source disconnect failed",
                exception_type=type(exc).__name__,
            )
            raise
        finally:
            self._connected = False
