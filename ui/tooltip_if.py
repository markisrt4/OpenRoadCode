# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Toolkit-independent tooltip presentation and lifecycle contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TooltipState:
    """Complete immutable tooltip presentation state."""

    text: str = ""
    visible: bool = False


class TooltipUiIf(ABC):
    """Present tooltip state without owning delay or cancellation policy."""

    @abstractmethod
    def set_tooltip_state(self, state: TooltipState) -> None:
        """Present the supplied snapshot.

        @param state Text and visibility to render.
        """
        ...


class TooltipRequestHandlerIf(ABC):
    """Handle semantic tooltip intent independently of toolkit events."""

    @abstractmethod
    def request_show(self, text: str) -> None:
        """Request delayed display.

        @param text Human-readable description of the control.
        """
        ...

    @abstractmethod
    def request_hide(self) -> None:
        """Dismiss the tooltip and invalidate pending display."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Idempotently release this tooltip's lifecycle."""
        ...


class TooltipFactoryIf(ABC):
    """Compose a fresh request handler for a mounted presentation view."""

    @abstractmethod
    def create(self, view: TooltipUiIf) -> TooltipRequestHandlerIf:
        """Bind a new tooltip session.

        @param view Presentation contract receiving snapshots.
        @return Request handler owned by the view lifecycle.
        """
        ...
