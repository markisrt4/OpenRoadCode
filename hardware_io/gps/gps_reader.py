from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass

import gps


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpsData:
    """Represent one normalized gpsd report.

    Position and altitude are expressed in degrees and meters; speed is in
    meters per second and track is in degrees.
    """
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    speed: float | None = None
    track: float | None = None
    mode: int | None = None
    satellites_visible: int | None = None
    satellites_used: int | None = None

    @property
    def has_fix(self) -> bool:
        """Return whether gpsd reports a positional fix.

        @retval True gpsd reports a 2D or 3D fix.
        @retval False gpsd reports no fix or an unknown mode.
        """
        return self.mode is not None and self.mode >= 2


GpsCallback = Callable[[GpsData], None]


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

    def open(self) -> None:
        """Opens a connection to gpsd."""
        if self._session is not None:
            return

        self._session = gps.gps(
            host=self._host,
            port=self._port,
            mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE,
        )

        LOGGER.info("Connected to gpsd at %s:%s", self._host, self._port)

    def close(self) -> None:
        """Closes the gpsd connection."""
        if self.is_running:
            self.stop()

        if self._session is not None:
            self._session.close()
            self._session = None

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

        self._thread = threading.Thread(
            target=self._run,
            name="GpsReader",
            daemon=True,
        )
        self._thread.start()

        LOGGER.info("GPS reader started")

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

        self._thread = None
        LOGGER.info("GPS reader stopped")

    def _run(self) -> None:
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

        except OSError:
            if not self._stop_event.is_set():
                LOGGER.exception("GPS connection failed")

        except Exception:
            if not self._stop_event.is_set():
                LOGGER.exception("Unexpected GPS reader failure")

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
