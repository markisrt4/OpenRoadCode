# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Interface for ambient light sensor hardware."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AmbientLightSensorIf(ABC):
    """Interface for reading illuminance from ambient light hardware."""

    @abstractmethod
    def start(self) -> None:
        """Initialize the sensor and prepare it for use."""

    @abstractmethod
    def stop(self) -> None:
        """Release resources owned by the sensor."""

    @property
    @abstractmethod
    def is_started(self) -> bool:
        """Return whether the sensor has been initialized.

        @retval True The sensor is initialized and readable.
        @retval False The sensor has not been started.
        """

    @abstractmethod
    def get_illuminance_lux(self) -> float:
        """Read ambient illuminance.

        @return Ambient illuminance in lux.
        """
