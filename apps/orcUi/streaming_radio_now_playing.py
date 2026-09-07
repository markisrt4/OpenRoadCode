# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Home-screen summary for streaming-radio playback."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from controllers.radio.streaming_radio_controller import StreamingRadioController
from ui.theme import ThemeBundle


class StreamingRadioNowPlaying(tk.Frame):
    """Present the current streaming-radio station on Home."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        controller: StreamingRadioController,
        theme: ThemeBundle,
        on_open: Callable[[], None],
    ) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.surface)
        self._controller = controller
        self._on_open = on_open
        self._ui = ui
        self._after_id: str | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._status = tk.Label(
            self,
            text="STREAMING RADIO",
            bg=ui.surface,
            fg=ui.accent_success,
            font=("Sans", 9, "bold"),
            anchor="w",
        )
        self._status.grid(row=0, column=0, sticky="ew", padx=12, pady=(9, 0))

        self._station = tk.Label(
            self,
            text="No stream playing",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 16, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=500,
        )
        self._station.grid(row=1, column=0, sticky="nsew", padx=12, pady=(2, 4))

        self._detail = tk.Label(
            self,
            text="Open Radio to choose a station",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 9),
            anchor="w",
        )
        self._detail.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 9))

        self._open = tk.Button(
            self,
            text="OPEN RADIO ›",
            command=self._on_open,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=10,
            pady=6,
        )
        self._open.grid(row=0, column=1, rowspan=3, sticky="ns", padx=(4, 10), pady=9)
        self._refresh()

    def destroy(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        super().destroy()

    def _refresh(self) -> None:
        if not self.winfo_exists():
            return
        current = self._controller.current_station
        playing = current is not None and self._controller.is_playing
        if playing and current is not None:
            self._status.configure(text="● NOW PLAYING", fg=self._ui.accent_success)
            self._station.configure(text=current.name)
            details: list[str] = []
            if current.state:
                details.append(current.state)
            if current.codec:
                details.append(current.codec)
            if current.bitrate_kbps is not None:
                details.append(f"{current.bitrate_kbps} kbps")
            self._detail.configure(text=" • ".join(details) or "Streaming radio")
        else:
            self._status.configure(text="STREAMING RADIO", fg=self._ui.accent_primary)
            self._station.configure(text="No stream playing")
            self._detail.configure(text="Open Radio to choose a station")
        self._after_id = self.after(750, self._refresh)
