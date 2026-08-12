# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Interface for items controlled by panel focus traversal."""

from __future__ import annotations

from abc import ABC, abstractmethod


class FocusableItemIf(ABC):
    """Interface implemented by a panel item that can receive focus."""

    @abstractmethod
    def set_focused(self, focused: bool) -> None:
        """Update the item's focused state and visual presentation.

        @param focused True when the item should present keyboard focus.
        """
        ...

    @abstractmethod
    def activate(self) -> None:
        """Perform the item's primary action."""
        ...

    def is_enabled(self) -> bool:
        """Return whether the item can currently receive focus.

        @return True when focus traversal may select this item.
        """
        return True
