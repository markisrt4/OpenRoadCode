import threading
from typing import Any

import gps

from modules.hardware.hardware_device_if import HardwareDeviceIf


class GPSDevice(HardwareDeviceIf):
    def __init__(self, name: str = "gps"):
        super().__init__(name)

        self.session = None
        self.thread = None

        self.lat: float | None = None
        self.lon: float | None = None
        self.alt: float | None = None
        self.speed: float | None = None
        self.track: float | None = None
        self.mode: int | None = None

    def start(self) -> None:
        if self.running:
            return

        try:
            self.session = gps.gps(mode=gps.WATCH_ENABLE)
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
        except Exception as exc:
            self.last_error = str(exc)
            self.running = False
            self.available = False

    def _run(self) -> None:
        while self.running:
            try:
                report = self.session.next()

                if report.get("class") != "TPV":
                    continue

                self.mode = getattr(report, "mode", None)
                self.lat = getattr(report, "lat", None)
                self.lon = getattr(report, "lon", None)
                self.alt = getattr(report, "alt", None)
                self.speed = getattr(report, "speed", None)
                self.track = getattr(report, "track", None)

                self.available = self.lat is not None and self.lon is not None

            except Exception as exc:
                self.last_error = str(exc)
                self.available = False

    def stop(self) -> None:
        self.running = False

    def has_fix(self) -> bool:
        return self.available

    def position(self) -> dict[str, float | None | bool]:
        return {
            "fix": self.has_fix(),
            "lat": self.lat,
            "lon": self.lon,
            "alt": self.alt,
            "speed": self.speed,
            "track": self.track,
        }

    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "running": self.running,
            "available": self.available,
            "mode": self.mode,
            "last_error": self.last_error,
            "position": self.position(),
        }
