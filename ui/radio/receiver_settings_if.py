# SPDX-License-Identifier: MIT
"""Toolkit-independent receiver settings state and requests."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReceiverSetting:
    serial: str
    identity: str | None
    usb_path: str
    owner: str | None
    available: bool
    phase: str | None = None


@dataclass(frozen=True, slots=True)
class ReceiverSettingsState:
    receivers: tuple[ReceiverSetting, ...]
    radio: str | None
    weather: str | None
    adsb: str | None


class ReceiverSettingsIf(Protocol):
    def refresh(
        self, on_result: Callable[[ReceiverSettingsState], None], on_error: Callable[[str], None]
    ) -> None:
        """!
        @brief Request the current assignments and connected receivers.
        @param on_result Receives the settings snapshot on the frontend thread.
        @param on_error Receives the refresh error on the frontend thread.
        """
        ...

    def save(
        self,
        radio: str | None,
        weather: str | None,
        adsb: str | None,
        on_result: Callable[[ReceiverSettingsState], None],
        on_error: Callable[[str], None],
    ) -> None:
        """!
        @brief Persist assignments for subsequent acquisitions.
        @param radio Broadcast, AM, NFM and airband receiver identity.
        @param weather NOAA receiver identity.
        @param adsb ADS-B receiver identity.
        @param on_result Receives updated settings on the frontend thread.
        @param on_error Receives the save error on the frontend thread.
        """
        ...
