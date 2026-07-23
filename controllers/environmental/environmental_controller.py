"""Controller for environmental sensor measurements."""

from __future__ import annotations

import math
import time
from collections import deque
from threading import Lock
from typing import Callable

from hardware_io.environmental import BarometricSensorIf

from .environmental_state import EnvironmentalState


class EnvironmentalController:
    """Read and process measurements from a barometric sensor.

    The controller calculates barometric altitude, relative altitude, and
    filtered vertical speed from pressure measurements.

    The hardware sensor remains responsible only for providing pressure and
    temperature values.
    """

    STANDARD_SEA_LEVEL_PRESSURE_PA = 101_325.0

    def __init__(
        self,
        sensor: BarometricSensorIf,
        *,
        sea_level_pressure_pa: float = STANDARD_SEA_LEVEL_PRESSURE_PA,
        vertical_speed_window_size: int = 8,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create an environmental controller.

        Args:
            sensor: Barometric pressure sensor implementation.
            sea_level_pressure_pa: Reference sea-level pressure used for
                absolute altitude calculations.
            vertical_speed_window_size: Number of altitude samples used to
                smooth vertical-speed calculations.
            monotonic_clock: Clock used for elapsed-time calculations.
        """
        if sea_level_pressure_pa <= 0.0:
            raise ValueError("sea_level_pressure_pa must be greater than zero")

        if vertical_speed_window_size < 2:
            raise ValueError(
                "vertical_speed_window_size must be at least two"
            )

        self._sensor = sensor
        self._sea_level_pressure_pa = sea_level_pressure_pa
        self._vertical_speed_window_size = vertical_speed_window_size
        self._clock = monotonic_clock

        self._started = False
        self._relative_altitude_reference_m: float | None = None
        self._altitude_history: deque[tuple[float, float]] = deque(
            maxlen=vertical_speed_window_size
        )
        self._latest_state: EnvironmentalState | None = None
        self._lock = Lock()

    @property
    def is_started(self) -> bool:
        """Return whether the controller and sensor are started."""

        with self._lock:
            return self._started

    @property
    def sea_level_pressure_pa(self) -> float:
        """Return the current sea-level pressure reference.

        @return Reference pressure in pascals.
        """

        with self._lock:
            return self._sea_level_pressure_pa

    @property
    def latest_state(self) -> EnvironmentalState | None:
        """Return the most recently calculated state.

        @return Latest snapshot, or ``None`` before the first successful read.
        """

        with self._lock:
            return self._latest_state

    def start(self) -> None:
        """Start the environmental sensor and reset calculated state."""

        with self._lock:
            if self._started:
                return

            self._sensor.start()
            self._started = True
            self._relative_altitude_reference_m = None
            self._altitude_history.clear()
            self._latest_state = None

    def stop(self) -> None:
        """Stop the environmental sensor."""

        with self._lock:
            if not self._started:
                return

            try:
                self._sensor.stop()
            finally:
                self._started = False
                self._altitude_history.clear()

    def read_state(self) -> EnvironmentalState:
        """Read the sensor and calculate environmental state.

        @return Pressure, temperature, altitude, and vertical-speed snapshot.
        @raises RuntimeError if the controller has not been started.
        """

        with self._lock:
            self._require_started()

            pressure_pa = self._sensor.get_pressure_pa()
            temperature_c = self._sensor.get_temperature_c()

            altitude_m = self.calculate_altitude_m(
                pressure_pa=pressure_pa,
                sea_level_pressure_pa=self._sea_level_pressure_pa,
            )

            if self._relative_altitude_reference_m is None:
                self._relative_altitude_reference_m = altitude_m

            relative_altitude_m = (
                altitude_m - self._relative_altitude_reference_m
            )

            sample_time = self._clock()
            self._altitude_history.append((sample_time, altitude_m))

            vertical_speed_mps = self._calculate_vertical_speed_mps()

            state = EnvironmentalState.create(
                pressure_pa=pressure_pa,
                temperature_c=temperature_c,
                altitude_m=altitude_m,
                relative_altitude_m=relative_altitude_m,
                vertical_speed_mps=vertical_speed_mps,
            )

            self._latest_state = state
            return state

    def set_sea_level_pressure_pa(self, pressure_pa: float) -> None:
        """Set the reference pressure used for absolute altitude.

        @param pressure_pa Positive sea-level reference pressure in pascals.
        @raises ValueError if ``pressure_pa`` is not positive.
        """

        if pressure_pa <= 0.0:
            raise ValueError("pressure_pa must be greater than zero")

        with self._lock:
            self._sea_level_pressure_pa = pressure_pa
            self._altitude_history.clear()
            self._latest_state = None

    def calibrate_altitude(
        self,
        known_altitude_m: float,
        *,
        pressure_pa: float | None = None,
    ) -> float:
        """Calibrate sea-level pressure using a known current altitude.

        @param known_altitude_m Known altitude above mean sea level in meters.
        @param pressure_pa Current pressure in pascals; when ``None``, read it
            from the configured sensor.
        @return Calculated sea-level pressure reference in pascals.
        @raises RuntimeError if the controller has not been started.
        @raises ValueError if the selected pressure is not positive.
        """

        with self._lock:
            self._require_started()

            current_pressure_pa = (
                self._sensor.get_pressure_pa()
                if pressure_pa is None
                else pressure_pa
            )

            if current_pressure_pa <= 0.0:
                raise ValueError("pressure_pa must be greater than zero")

            sea_level_pressure_pa = (
                current_pressure_pa
                / math.pow(
                    1.0 - (known_altitude_m / 44_330.0),
                    5.255,
                )
            )

            self._sea_level_pressure_pa = sea_level_pressure_pa
            self._altitude_history.clear()
            self._latest_state = None

            return sea_level_pressure_pa

    def reset_relative_altitude(self) -> None:
        """Set the current altitude as the relative-altitude zero point."""

        with self._lock:
            self._require_started()

            pressure_pa = self._sensor.get_pressure_pa()
            altitude_m = self.calculate_altitude_m(
                pressure_pa=pressure_pa,
                sea_level_pressure_pa=self._sea_level_pressure_pa,
            )

            self._relative_altitude_reference_m = altitude_m
            self._altitude_history.clear()

    @staticmethod
    def calculate_altitude_m(
        *,
        pressure_pa: float,
        sea_level_pressure_pa: float,
    ) -> float:
        """Calculate barometric altitude in meters.

        This uses the standard atmosphere approximation and assumes a
        tropospheric temperature lapse rate.

        @param pressure_pa Measured atmospheric pressure in pascals.
        @param sea_level_pressure_pa Sea-level reference pressure in pascals.
        @return Estimated altitude above mean sea level in meters.
        @raises ValueError if either pressure is not positive.
        """

        if pressure_pa <= 0.0:
            raise ValueError("pressure_pa must be greater than zero")

        if sea_level_pressure_pa <= 0.0:
            raise ValueError(
                "sea_level_pressure_pa must be greater than zero"
            )

        pressure_ratio = pressure_pa / sea_level_pressure_pa

        return 44_330.0 * (
            1.0 - math.pow(pressure_ratio, 1.0 / 5.255)
        )

    def _calculate_vertical_speed_mps(self) -> float:
        if len(self._altitude_history) < 2:
            return 0.0

        oldest_time, oldest_altitude = self._altitude_history[0]
        newest_time, newest_altitude = self._altitude_history[-1]

        elapsed_s = newest_time - oldest_time
        if elapsed_s <= 0.0:
            return 0.0

        return (newest_altitude - oldest_altitude) / elapsed_s

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError(
                "Environmental controller has not been started"
            )

    def __enter__(self) -> EnvironmentalController:
        self.start()
        return self

    def __exit__(
        self,
        _exception_type: object,
        _exception: object,
        _traceback: object,
    ) -> None:
        self.stop()
