# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Hardware-neutral road-camera control profile contract."""

from abc import ABC, abstractmethod
from enum import Enum


class CameraProfile(str, Enum):
    """Hardware profiles understood by road-camera controllers."""

    DAY = "day"
    LOW_LIGHT = "low_light"


class CameraControlsIf(ABC):
    """Apply and restore camera hardware profiles."""

    @property
    @abstractmethod
    def current_profile(self) -> CameraProfile | None:
        """Return the most recently applied profile.

        @return Current profile, or None when hardware state is unknown.
        """
        ...

    @abstractmethod
    def probe_supported_profiles(self) -> frozenset[CameraProfile]:
        """Discover profiles supported by the currently connected device.

        @return Immutable set of profiles whose required controls are supported.
        """
        ...

    @abstractmethod
    def apply(self, profile: CameraProfile) -> None:
        """Apply a hardware profile.

        @param profile Hardware profile to apply.
        """
        ...

    @abstractmethod
    def invalidate(self) -> None:
        """Forget cached profile state after the device changes."""
        ...

    @abstractmethod
    def restore_day_defaults(self) -> None:
        """Restore the conservative daytime hardware profile."""
        ...
