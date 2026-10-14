# SPDX-License-Identifier: MIT
"""Test semantic live/estimated position presentation in shell chrome."""

from types import SimpleNamespace
from unittest.mock import Mock

from apps.orcUi.frontend.tk.shell_view import OrcUiShellView
from apps.orcUi.navigation_presenter import PositionPresentationState


def shell():
    view = OrcUiShellView.__new__(OrcUiShellView)
    view._position_status_label = Mock()
    view._position_status_label.winfo_exists.return_value = True
    view._theme = SimpleNamespace(
        ui=SimpleNamespace(accent_warning="amber", text="white", text_muted="gray")
    )
    return view


def test_cached_fix_is_presented_as_estimated():
    view = shell()

    view.set_position_state(PositionPresentationState(
        latitude_deg=42.3,
        longitude_deg=-83.0,
        fix_mode=3,
        is_cached=True,
    ))

    view._position_status_label.configure.assert_called_once_with(
        text="GPS EST   ◌🚗",
        fg="amber",
    )


def test_live_fix_replaces_estimated_status():
    view = shell()

    view.set_position_state(PositionPresentationState(
        latitude_deg=42.3,
        longitude_deg=-83.0,
        fix_mode=3,
    ))

    view._position_status_label.configure.assert_called_once_with(
        text="GPS LIVE   🚗",
        fg="white",
    )
