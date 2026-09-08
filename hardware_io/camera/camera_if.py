# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation-neutral camera capture contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CameraFrame:
    """One captured image and its capture metadata.

    ``image`` is deliberately backend-neutral. The V4L2/OpenCV implementation
    supplies a BGR ``numpy.ndarray`` while consumers depend only on this
    contract. This keeps camera ownership out of UI and perception code.
    """

    image: Any
    timestamp_s: float
    sequence: int


class CameraIf(ABC):
    """Interface for a source capable of producing camera frames."""

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """Return whether the camera device is currently open."""

    @abstractmethod
    def open(self) -> None:
        """Open and configure the camera device."""

    @abstractmethod
    def read(self) -> CameraFrame:
        """Capture and return the next frame."""

    @abstractmethod
    def close(self) -> None:
        """Release the camera device."""

    def __enter__(self) -> "CameraIf":
        self.open()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
