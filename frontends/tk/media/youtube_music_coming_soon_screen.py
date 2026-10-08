# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Placeholder screen for the planned YouTube Music integration."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode


class YouTubeMusicComingSoonScreen(TkScreen):
    """Present YouTube Music as a planned feature without launching a runtime."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        back_action: Callable[[], None],
        theme_bundle: Callable[[], ThemeBundle],
    ) -> None:
        super().__init__(ScreenId("youtube_music"))
        self._host = host
        self._back_action = back_action
        self._theme_bundle = theme_bundle

    def set_theme_mode(self, _mode: ThemeMode) -> None:
        self.show()

    def show(self) -> None:
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("YouTube Music")
        self._host.set_screen_status("Coming soon")

        theme = self._theme_bundle().ui
        root = tk.Frame(self._host.screen_parent, bg=theme.background)
        root.pack(fill=tk.BOTH, expand=True)

        panel = tk.Frame(
            root,
            bg=theme.surface,
            highlightthickness=1,
            highlightbackground=theme.border,
        )
        panel.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        center = tk.Frame(panel, bg=theme.surface)
        center.place(relx=0.5, rely=0.46, anchor="center")

        tk.Label(
            center,
            text="▶",
            bg=theme.surface,
            fg="#FF0000",
            font=("Sans", 42, "bold"),
        ).pack(pady=(0, 8))
        tk.Label(
            center,
            text="YOUTUBE MUSIC",
            bg=theme.surface,
            fg=theme.text,
            font=("Sans", 24, "bold"),
        ).pack()
        tk.Label(
            center,
            text="COMING SOON",
            bg=theme.surface,
            fg="#FF0000",
            font=("Sans", 14, "bold"),
        ).pack(pady=(6, 10))
        tk.Label(
            center,
            text="YouTube Music integration is planned for a future OpenRoadCode release.",
            bg=theme.surface,
            fg=theme.text_muted,
            font=("Sans", 13),
        ).pack()

        tk.Button(
            panel,
            text="‹  BACK TO MEDIA",
            command=self._back_action,
            bg=theme.control_background,
            fg=theme.control_text,
            activebackground=theme.control_active,
            activeforeground=theme.text,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 13, "bold"),
            padx=18,
            pady=9,
        ).pack(side=tk.BOTTOM, pady=18)
