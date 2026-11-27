# SPDX-License-Identifier: MIT
"""Regression coverage for grouped context navigation."""

from types import SimpleNamespace
from unittest.mock import Mock

from apps.orcUi.frontend.tk.context_rail import ContextRail


def _rail():
    rail = object.__new__(ContextRail)
    rail._group = "AUTOMOTIVE"
    rail._group_pages = {"AUTOMOTIVE": 0, "PERSONAL": 0}
    rail._page_index = 0
    rail._calendar_factory = Mock()
    rail._rebuild = Mock()
    rail._show_page = Mock()
    rail._pages = lambda: (1, 2, 3) if rail._group == "AUTOMOTIVE" else (1,)
    return rail


def test_group_switch_preserves_automotive_page():
    rail = _rail()
    rail._next_page()
    rail._select_group("PERSONAL")
    assert rail._page_index == 0
    rail._select_group("AUTOMOTIVE")
    assert rail._page_index == 1


def test_selection_restored_on_new_rail():
    rail = _rail()
    rail._next_page()
    rail._select_group("PERSONAL")
    restored = _rail()
    restored.restore_selection(rail.selection())
    assert restored._group == "PERSONAL"
    restored._select_group("AUTOMOTIVE")
    assert restored._page_index == 1


def test_horizontal_swipe_advances_and_reverses():
    rail = _rail()
    rail._begin_swipe(SimpleNamespace(x_root=100, y_root=100))
    rail._end_swipe(SimpleNamespace(x_root=30, y_root=105))
    assert rail._page_index == 1
    rail._begin_swipe(SimpleNamespace(x_root=30, y_root=105))
    rail._end_swipe(SimpleNamespace(x_root=100, y_root=100))
    assert rail._page_index == 0


def test_vertical_swipe_does_not_change_page():
    rail = _rail()
    rail._begin_swipe(SimpleNamespace(x_root=100, y_root=100))
    rail._end_swipe(SimpleNamespace(x_root=30, y_root=200))
    assert rail._page_index == 0


def test_single_page_group_ignores_swipe():
    rail = _rail()
    rail._select_group("PERSONAL")
    rail._begin_swipe(SimpleNamespace(x_root=100, y_root=100))
    rail._end_swipe(SimpleNamespace(x_root=30, y_root=100))
    rail._show_page.assert_not_called()
