# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.tk.media.browser_return_overlay import BrowserReturnOverlay
from frontends.tk.media.spotify_services_if import BrowserMediaPlayerIf


class YouTubePanel(tk.Frame):
    """Car UI controls for YouTube browsing and search."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        player: BrowserMediaPlayerIf,
        default_url: str,
        display: str,
        set_status: Callable[[str], None],
        on_return: Callable[[], None],
        colors: dict[str, str],
    ) -> None:
        super().__init__(parent, bg=colors["app_bg"])
        self._player = player
        self._display = display
        self._set_status = set_status
        self._colors = colors
        self._default_url = default_url
        self._target = tk.StringVar(value=default_url)
        self._return_overlay = BrowserReturnOverlay(
            self,
            command=on_return,
            background=colors["tile_accent"],
            foreground=colors["tile_title"],
            active_background=colors["tile_border"],
        )
        self._build_ui()

    def open_home(self) -> None:
        """Open the YouTube home page immediately."""
        self._target.set(self._default_url)
        self._open()

    def destroy(self) -> None:
        self._return_overlay.hide()
        super().destroy()

    def _build_ui(self) -> None:
        card = tk.Frame(
            self,
            bg=self._colors["tile_bg"],
            highlightthickness=2,
            highlightbackground=self._colors["tile_border"],
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            card,
            text="YOUTUBE",
            bg=self._colors["tile_bg"],
            fg=self._colors["tile_title"],
            font=("DejaVu Sans", 28, "bold"),
        ).pack(pady=(24, 8))
        tk.Label(
            card,
            text="Enter a search or paste a YouTube URL",
            bg=self._colors["tile_bg"],
            fg=self._colors["tile_subtitle"],
            font=("DejaVu Sans", 15),
        ).pack(pady=(0, 14))

        entry = tk.Entry(
            card,
            textvariable=self._target,
            font=("DejaVu Sans", 14),
            bg="#ffffff",
            fg="#111111",
            insertbackground="#111111",
        )
        entry.pack(fill="x", padx=28, ipady=10)
        entry.bind("<Return>", lambda _event: self._open())

        controls = tk.Frame(card, bg=self._colors["tile_bg"])
        controls.pack(pady=22)
        self._button(
            controls,
            text="OPEN YOUTUBE",
            command=self._open,
        ).pack(side="left", padx=8)
        self._button(
            controls,
            text="STOP",
            command=self._stop,
        ).pack(side="left", padx=8)

        tk.Label(
            card,
            text=(
                "YouTube opens in a dedicated browser window. "
                "Your login is retained for future sessions."
            ),
            bg=self._colors["tile_bg"],
            fg=self._colors["tile_detail"],
            font=("DejaVu Sans", 11),
            wraplength=620,
        ).pack(pady=(0, 18))

    def _button(
        self,
        parent: tk.Widget,
        *,
        text: str,
        command: Callable[[], None],
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self._colors["tile_accent"],
            fg=self._colors["tile_title"],
            activebackground=self._colors["tile_border"],
            activeforeground=self._colors["tile_title"],
            font=("DejaVu Sans", 15, "bold"),
            relief="flat",
            cursor="hand2",
            padx=20,
            pady=12,
        )

    def _open(self) -> None:
        try:
            self.update_idletasks()
            self._player.play(
                self._target.get(),
                display=self._display,
                window_position=(
                    self.winfo_rootx(),
                    self.winfo_rooty(),
                ),
                window_size=(
                    max(1, self.winfo_width()),
                    max(1, self.winfo_height()),
                ),
            )
        except Exception as error:
            self._set_status(f"YouTube launch failed: {error}")
            return

        self._return_overlay.show(
            x=self.winfo_rootx() + 12,
            y=self.winfo_rooty() + 12,
        )
        self._set_status(f"YouTube opened on {self._display}")

    def _stop(self) -> None:
        self._return_overlay.hide()
        self._player.stop()
        self._set_status("YouTube stopped")
