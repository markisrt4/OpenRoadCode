# SPDX-License-Identifier: MIT
"""Toolkit-independent application notification contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class NotificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Notification:
    """Semantic event, not a request to draw on a particular widget."""

    code: str
    title: str
    message: str
    severity: NotificationSeverity
    source: str

    def __post_init__(self) -> None:
        for field in ("code", "title", "message", "source"):
            if not getattr(self, field).strip():
                raise ValueError(f"Notification {field} must not be empty")


class NotificationSinkIf(Protocol):
    """Receive notifications independently of the chosen UI toolkit."""

    def publish(self, notification: Notification) -> None:
        """Deliver a semantic application notification.
        @param notification Notification to deliver.
        """
        ...
