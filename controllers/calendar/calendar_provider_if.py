# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Read-only foundation for pluggable calendar providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .calendar_models import CalendarCapabilities, CalendarEvent


class CalendarProviderIf(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> CalendarCapabilities:
        """Describe supported provider operations.

        @return Supported capabilities.
        """

    @abstractmethod
    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """Return events overlapping the half-open interval [start, end).

        @param start Inclusive window start.
        @param end Exclusive window end.
        @return Overlapping events.
        """
