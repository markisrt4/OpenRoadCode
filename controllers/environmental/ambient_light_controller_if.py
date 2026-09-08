# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Public interface for ambient light controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .ambient_light_state import AmbientLightState


class AmbientLightControllerIf(ABC):
    """Provide ambient illuminance state."""

    @property
    @abstractmethod
    def is_started(self) -> bool:
        """Return whether the controller is ready to read state.

        @return True when the controller has started and can read state.
        """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether ambient light support is available.

        @return True when an ambient light source is available.
        """

    @property
    @abstractmethod
    def status_message(self) -> str | None:
        """Return an availability message, if one applies.

        @return Availability/status message, or None when no message applies.
        """

    @property
    @abstractmethod
    def latest_state(self) -> AmbientLightState | None:
        """Return the latest state, or ``None`` before the first read.

        @return Most recently sampled ambient light state, or None when unread.
        """

    @abstractmethod
    def start(self) -> None:
        """Start the controller and its ambient light sensor."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the controller and its ambient light sensor."""

    @abstractmethod
    def read_state(self) -> AmbientLightState:
        """Read and return the current ambient light state.

        @return Newly sampled ambient light state.
        """
