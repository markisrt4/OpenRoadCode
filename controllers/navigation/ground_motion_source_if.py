# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Source contract for normalized ground-motion updates."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from controllers.navigation.navigation_state import GroundMotionState


GroundMotionStateCallback = Callable[[GroundMotionState], None]


class GroundMotionSourceIf(ABC):
    """Publish ground motion independently of the underlying provider."""

    @abstractmethod
    def start(self, callback: GroundMotionStateCallback) -> None:
        """Start publishing normalized ground-motion snapshots."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop publishing ground-motion snapshots."""
        ...
