# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Home layout extension for feature-owned presentation slots."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from apps.orcUi.context_rail import ContextRail
from apps.orcUi.home_map_panel import HomeMapPanel
from apps.orcUi.orc_ui_app import OrcUiApp


class ComposedHomeShell(OrcUiApp):
    """Expose neutral Home slots without owning radio or media services."""

    def __init__(self, *, map_runtime) -> None:
        self._home_radio_factory: Callable[[tk.Misc], tk.Widget] | None = None
        super().__init__(map_runtime=map_runtime)

    def set_home_radio_factory(self, factory: Callable[[tk.Misc], tk.Widget] | None) -> None:
        """Install a radio-owned Home summary without coupling the shell to radio."""
        self._home_radio_factory = factory
        if self._active_nav == "HOME":
            self._show_home()

    def _show_home(self) -> None:
        self._clear_content()
        self._active_nav = "HOME"
        self._paint_nav()
        ui = self._theme.ui
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_columnconfigure(1, weight=0, minsize=ContextRail.WIDTH)
        self._content.grid_rowconfigure(0, weight=3)
        self._content.grid_rowconfigure(1, weight=2)
        self._home_map_panel = HomeMapPanel(self._content, theme=self._theme)
        self._home_map_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
        self._context_rail = ContextRail(self._content, on_expand=self._show_context_full_panel, theme=self._theme)
        self._context_rail.update_vehicle_state(self._vehicle_state)
        self._context_rail.update_position_state(self._position_state)
        self._context_rail.update_attitude_state(self._attitude_state)
        self._context_rail.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))
        lower = tk.Frame(self._content, bg=ui.background)
        lower.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(5, 0))
        lower.grid_columnconfigure(0, weight=4)
        lower.grid_columnconfigure(1, weight=1)
        lower.grid_rowconfigure(0, weight=1)
        radio = self._panel(lower, "RADIO", ui.accent_warning)
        radio.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        if self._home_radio_factory is None:
            self._summary(radio, "No radio active", "Choose RF or streaming")
        else:
            self._home_radio_factory(radio).pack(fill=tk.BOTH, expand=True)
        media = self._panel(lower, "MEDIA", ui.accent_primary)
        media.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        if self._home_media_factory is None:
            self._summary(media, "No media", "Playback service")
        else:
            self._home_media_factory(media).pack(fill=tk.BOTH, expand=True)
        self._root.update_idletasks()
        self._start_map_renderer(self._home_map_panel.map_host_window_id)
