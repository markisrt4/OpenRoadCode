# SPDX-License-Identifier: MIT
"""Toolkit-independent audio settings state and requests."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class AudioAction(Enum):
    REFRESH = "refresh"
    SELECT_OUTPUT = "select_output"
    SCAN = "scan"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


@dataclass(frozen=True, slots=True)
class AudioDevice:
    identifier: str
    name: str
    selected: bool = False
    paired: bool = False


@dataclass(frozen=True, slots=True)
class AudioSettingsState:
    outputs: tuple[AudioDevice, ...] = ()
    receivers: tuple[AudioDevice, ...] = ()
    warnings: tuple[str, ...] = ()


class AudioSettingsIf(Protocol):
    def request(
        self,
        action: AudioAction,
        identifier: str,
        on_result: Callable[[AudioSettingsState], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Submit an audio settings operation without blocking the frontend.

        @param action Requested audio or Bluetooth operation.
        @param identifier Output name or Bluetooth address, when applicable.
        @param on_result Receives the refreshed state on the frontend thread.
        @param on_error Receives an actionable error on the frontend thread.
        """
        ...
