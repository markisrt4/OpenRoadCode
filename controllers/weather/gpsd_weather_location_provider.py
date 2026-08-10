"""GPSD-backed weather location selection."""

from controllers.weather.weather_snapshot import WeatherLocation


class GpsdWeatherLocationProvider:
    """Read a current weather location from GPSD when a fix exists."""

    def __init__(self, host: str = "127.0.0.1", port: int = 2947) -> None:
        self._host = host
        self._port = port

    def get_location(self) -> WeatherLocation:
        """Return the current GPS fix.

        @return GPS-derived location.
        @exception RuntimeError if GPSD support or a position fix is absent.
        """
        try:
            import gpsd
        except ImportError as error:
            raise RuntimeError("gpsd-py3 is unavailable") from error
        gpsd.connect(host=self._host, port=self._port)
        packet = gpsd.get_current()
        if packet.mode < 2 or packet.lat is None or packet.lon is None:
            raise RuntimeError("GPS fix is unavailable")
        return WeatherLocation(
            latitude=float(packet.lat),
            longitude=float(packet.lon),
            name=f"{packet.lat:.5f}, {packet.lon:.5f}",
            source="GPSD",
        )
