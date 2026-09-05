# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public contracts for Google Earth camera control."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EarthCameraView:
    """Desired Google Earth camera state."""

    latitude_deg: float
    longitude_deg: float
    heading_deg: float | None = None
    tilt_deg: float | None = None
    altitude_m: float | None = None


class EarthCameraControllerIf(ABC):
    """Apply camera state to one Google Earth control mechanism."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the controller's short diagnostic name."""
        ...

    @abstractmethod
    def available(self) -> bool:
        """Return whether this control mechanism can currently be used."""
        ...

    @abstractmethod
    def set_view(self, view: EarthCameraView) -> bool:
        """Apply the requested view and report whether it succeeded."""
        ...
