# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import threading

from common.logging.diagnostics import ComponentLog, diagnostic_action
from common.logging.structured import current_operation, operation

import gps

try:
    from gps.client import dictwrapper
except ModuleNotFoundError:
    dictwrapper = gps.dictwrapper

from hardware_io.gps.gps_types import GpsCallback, GpsData


class _Python3GpsSession(gps.gps):
    """Adapt older gpsd Python bindings to Python 3's JSON API."""

    def unpack(self, buffer: str) -> None:
        try:
            self.data = dictwrapper(json.loads(buffer.strip()))
        except ValueError as exc:
            raise ValueError(f"Invalid gpsd JSON report: {buffer!r}") from exc

        if hasattr(self.data, "satellites"):
            self.data.satellites = [
                dictwrapper(satellite)
                for satellite in self.data.satellites
            ]


class GpsReader:
    """
    Reads GPS data from gpsd.

    The reader reports GPS values as they are received. It does not open or
    configure the physical GPS device and does not apply application-specific
    behavior. The physical device is owned and managed by gpsd.
    """

    def __init__(
        self,
        callback: GpsCallback | None = None,
        host: str = "127.0.0.1",
        port: str = "2947",
    ) -> None:
        if callback is not None and not callable(callback):
            raise TypeError("callback must be callable")

        self._diagnostics = ComponentLog("navigation.gps", "gps")
        self._operation_id = None
        self._callback = callback
        self._host = host
        self._port = port

        self._session: gps.gps | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._satellites_visible: int | None = None
        self._satellites_used: int | None = None

    @property
    def is_running(self) -> bool:
        """Return whether the background gpsd reader thread is active."""
        return self._thread is not None and self._thread.is_alive()

    @diagnostic_action("open")
    def open(self) -> None:
        """Opens a connection to gpsd."""
        if self._session is not None:
            return

        self._session = _Python3GpsSession(
            host=self._host,
            port=self._port,
            mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE,
        )

        self._diagnostics.changed("connection", "connected")

    @diagnostic_action("close")
    def close(self) -> None:
        """Closes the gpsd connection."""
        if self.is_running:
            self.stop()

        if self._session is not None:
            self._session.close()
            self._session = None
            self._diagnostics.changed("connection", "disconnected")

    @diagnostic_action("start")
    def start(self, callback: GpsCallback | None = None) -> None:
        """Starts reading GPS data in a background thread."""
        if callback is not None:
            if not callable(callback):
                raise TypeError("callback must be callable")
            self._callback = callback

        if self._callback is None:
            raise ValueError("A callback is required before starting")

        if self.is_running:
            return

        self.open()
        self._stop_event.clear()

        self._operation_id = current_operation()
        self._thread = threading.Thread(
            target=self._run, args=(self._operation_id,),
            name="GpsReader",
            daemon=True,
        )
        self._thread.start()

    @diagnostic_action("stop")
    def stop(self) -> None:
        """Stops the GPS reader."""
        self._stop_event.set()

        if self._session is not None:
            self._session.close()
            self._session = None

        if (
            self._thread is not None
            and self._thread.is_alive()
            and self._thread is not threading.current_thread()
        ):
            self._thread.join(timeout=1.0)

        if self._thread is not None and self._thread.is_alive():
            self._diagnostics.failed("join", operation_id=self._operation_id, reason="timeout")
        else:
            self._thread = None
            self._diagnostics.succeeded("join", self._operation_id)
        self._diagnostics.changed("connection", "disconnected", self._operation_id)

    def _run(self, operation_id=None) -> None:
        with operation(operation_id or self._operation_id):
            self._diagnostics.changed("reader", "running")
            try:
                self._read_reports()
            finally:
                self._diagnostics.changed("reader", "stopped")

    def _read_reports(self) -> None:
        try:
            if self._session is None:
                raise RuntimeError("GPS session is not open")

            for report in self._session:
                if self._stop_event.is_set():
                    break

                report_class = report.get("class")

                if report_class == "SKY":
                    self._update_satellite_counts(report)
                    continue

                if report_class != "TPV":
                    continue

                self._publish(
                    GpsData(
                        latitude=report.get("lat"),
                        longitude=report.get("lon"),
                        altitude=report.get("alt"),
                        speed=report.get("speed"),
                        track=report.get("track"),
                        mode=report.get("mode"),
                        satellites_visible=self._satellites_visible,
                        satellites_used=self._satellites_used,
                    )
                )

                self._diagnostics.succeeded("read")

        except Exception as error:
            if not self._stop_event.is_set():
                self._diagnostics.failed("read", error)

    def _update_satellite_counts(self, report: gps.gpsdata) -> None:
        satellites = report.get("satellites") or []
        self._satellites_visible = len(satellites)
        self._satellites_used = sum(
            1 for satellite in satellites if satellite.get("used", False)
        )

    def _publish(self, data: GpsData) -> None:
        callback = self._callback
        if callback is not None:
            callback(data)

    def __enter__(self) -> GpsReader:
        self.open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
