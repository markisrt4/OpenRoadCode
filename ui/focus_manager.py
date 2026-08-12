# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable focus traversal for an ordered collection of panel items."""

from __future__ import annotations

from collections.abc import Iterable

from ui.focusable_item_if import FocusableItemIf


class FocusManager:
    """Own focus state and traversal for one panel."""

    def __init__(
        self,
        items: Iterable[FocusableItemIf] = (),
        *,
        wrap: bool = True,
    ) -> None:
        self._items = list(items)
        self._wrap = wrap
        self._focused_index: int | None = None
        self.focus_first()

    @property
    def focused_item(self) -> FocusableItemIf | None:
        """Return the currently focused item, if any."""
        if self._focused_index is None:
            return None
        return self._items[self._focused_index]

    @property
    def focused_index(self) -> int | None:
        """Return the current index, if any."""
        return self._focused_index

    def set_items(self, items: Iterable[FocusableItemIf]) -> None:
        """Replace the traversal order and focus the first enabled item."""
        self.clear_focus()
        self._items = list(items)
        self.focus_first()

    def focus_first(self) -> bool:
        """Focus the first enabled item."""
        index = self._find_enabled_index(
            start=0,
            step=1,
            include_start=True,
            wrap=False,
        )
        return self._set_focused_index(index)

    def focus_next(self) -> bool:
        """Move focus to the next enabled item."""
        return self._move_focus(step=1)

    def focus_previous(self) -> bool:
        """Move focus to the previous enabled item."""
        return self._move_focus(step=-1)

    def activate_focused(self) -> bool:
        """Activate the focused item."""
        item = self.focused_item
        if item is None or not item.is_enabled():
            return False
        item.activate()
        return True

    def clear_focus(self) -> None:
        """Remove focus from the current item."""
        item = self.focused_item
        if item is not None:
            item.set_focused(False)
        self._focused_index = None

    def _move_focus(self, *, step: int) -> bool:
        if not self._items:
            return False
        if self._focused_index is None:
            return self.focus_first()

        index = self._find_enabled_index(
            start=self._focused_index,
            step=step,
            include_start=False,
            wrap=self._wrap,
        )
        return self._set_focused_index(index)

    def _find_enabled_index(
        self,
        *,
        start: int,
        step: int,
        include_start: bool,
        wrap: bool,
    ) -> int | None:
        item_count = len(self._items)
        if item_count == 0:
            return None

        offset_start = 0 if include_start else 1
        for offset in range(offset_start, item_count + offset_start):
            raw_index = start + (offset * step)
            if wrap:
                index = raw_index % item_count
            elif not 0 <= raw_index < item_count:
                break
            else:
                index = raw_index

            if self._items[index].is_enabled():
                return index

        return None

    def _set_focused_index(self, index: int | None) -> bool:
        if index is None:
            return False
        if index == self._focused_index:
            return True

        current = self.focused_item
        if current is not None:
            current.set_focused(False)

        self._focused_index = index
        self._items[index].set_focused(True)
        return True
