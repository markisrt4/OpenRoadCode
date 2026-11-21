# SPDX-License-Identifier: MIT
"""Error dialog lifecycle tests without requiring an X display."""
from unittest.mock import MagicMock, patch

from apps.orcUi.frontend.tk.error_dialog import ErrorDialog


def test_dismiss_is_safe_without_window():
    dialog = ErrorDialog(MagicMock(), lambda: MagicMock())
    dialog.dismiss()
    assert dialog._window is None


def test_dismiss_closes_window_once():
    dialog = ErrorDialog(MagicMock(), lambda: MagicMock())
    window = MagicMock()
    window.winfo_exists.return_value = True
    dialog._window = window
    dialog.dismiss()
    window.destroy.assert_called_once_with()
    assert dialog._window is None
    dialog.dismiss()
    window.destroy.assert_called_once_with()


def test_show_replaces_existing_dialog():
    root = MagicMock()
    theme = MagicMock()
    dialog = ErrorDialog(root, lambda: theme)
    old = MagicMock()
    old.winfo_exists.return_value = True
    dialog._window = old
    with patch("apps.orcUi.frontend.tk.error_dialog.tk.Toplevel") as top, \
         patch("apps.orcUi.frontend.tk.error_dialog.tk.Label"), \
         patch("apps.orcUi.frontend.tk.error_dialog.tk.Button"):
        dialog.show("ADS-B Map Unavailable", "Connection refused")
    old.destroy.assert_called_once_with()
    top.assert_called_once_with(root)
    assert dialog._window is top.return_value
    top.return_value.title.assert_called_once_with("ADS-B Map Unavailable")
