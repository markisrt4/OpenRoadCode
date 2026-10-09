# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Exercise orcUi borderless development-window behavior with real Tk."""

import os
import tkinter as tk
from unittest.mock import Mock, patch

import pytest

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp


def test_escape_restores_decorations_without_closing_orc() -> None:
    """Keep the application alive when Escape leaves borderless mode."""
    environment = {
        "OPENROAD_INSTALL_TARGET": "linux-dev",
        "ORCUI_FULLSCREEN": "0",
        "ORCUI_BORDERLESS": "1",
        "ORCUI_GEOMETRY": "1280x720",
    }
    with patch.dict(os.environ, environment, clear=False):
        try:
            app = OrcUiApp(lifecycle_handler=Mock())
        except tk.TclError as error:
            pytest.skip(f"Tk display unavailable: {error}")
    try:
        assert app._borderless
        assert bool(app._root.overrideredirect())

        app._root.update()
        app._root.focus_force()
        app._root.event_generate("<Escape>")
        app._root.update()

        assert not app._borderless
        assert not bool(app._root.overrideredirect())
        assert app._root.winfo_exists()
    finally:
        app._root.destroy()
