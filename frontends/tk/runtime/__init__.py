# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk display and window runtime helpers."""

from frontends.tk.runtime.display_runtime import configure_display
from frontends.tk.runtime.window_runtime import apply_fullscreen

__all__ = ["apply_fullscreen", "configure_display"]
