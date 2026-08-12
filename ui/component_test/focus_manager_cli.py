# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Command-line component test for panel focus traversal."""

from __future__ import annotations

from dataclasses import dataclass

from ui.focus_manager import FocusManager
from ui.focusable_item_if import FocusableItemIf


@dataclass
class MockFocusableItem(FocusableItemIf):
    """Simple focusable item used by the component test."""

    name: str
    enabled: bool = True
    focused: bool = False
    activation_count: int = 0

    def set_focused(self, focused: bool) -> None:
        self.focused = focused
        state = "FOCUSED" if focused else "unfocused"
        print(f"{self.name}: {state}")

    def activate(self) -> None:
        self.activation_count += 1
        print(f"{self.name}: ACTIVATED")

    def is_enabled(self) -> bool:
        return self.enabled


def _assert_focused(
    manager: FocusManager,
    expected: MockFocusableItem,
) -> None:
    assert manager.focused_item is expected
    assert expected.focused


def main() -> int:
    first = MockFocusableItem("First")
    disabled = MockFocusableItem("Disabled", enabled=False)
    third = MockFocusableItem("Third")

    manager = FocusManager((first, disabled, third))

    print()
    print("Initial focus")
    print("-------------")
    _assert_focused(manager, first)

    print()
    print("Move next, skipping disabled item")
    print("---------------------------------")
    assert manager.focus_next()
    _assert_focused(manager, third)

    print()
    print("Wrap to first item")
    print("------------------")
    assert manager.focus_next()
    _assert_focused(manager, first)

    print()
    print("Move previous with wrapping")
    print("---------------------------")
    assert manager.focus_previous()
    _assert_focused(manager, third)

    print()
    print("Activate focused item")
    print("---------------------")
    assert manager.activate_focused()
    assert third.activation_count == 1

    print()
    print("All focus manager component tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
