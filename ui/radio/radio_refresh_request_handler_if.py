# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Refresh requests emitted by a radio UI."""

from abc import ABC, abstractmethod


class RadioRefreshRequestHandlerIf(ABC):
    """Handle requests to republish current radio state and telemetry."""

    @abstractmethod
    def request_radio_refresh(self) -> None:
        """Request the latest radio state and telemetry."""
        ...
