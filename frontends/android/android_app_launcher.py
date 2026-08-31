"""Frontend contract for launching Android applications."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class AndroidAppLauncherError(RuntimeError):
    """Raised when an Android frontend cannot satisfy a launch request."""


@dataclass(frozen=True)
class AndroidApp:
    """An Android application exposed by the active Android runtime."""

    name: str
    package: str


class AndroidAppLauncher(ABC):
    """Runtime-independent interface used to expose Android applications."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the Android application runtime is usable."""

    @abstractmethod
    def list_apps(self) -> tuple[AndroidApp, ...]:
        """Return applications exposed by the Android runtime."""

    @abstractmethod
    def launch(self, package: str) -> None:
        """Launch an Android application by package name."""
