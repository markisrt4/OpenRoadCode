# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Home-screen radio summary with streaming playback awareness."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from controllers.radio.streaming_radio_controller import StreamingRadioController
from ui.theme import ThemeBundle


class StreamingRadioNowPlaying(tk.Frame):
    """Present neutral radio state and current streaming playback on Home."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        controller: StreamingRadioController,
        theme: ThemeBundle,
        on_open_rf: Callable[[], None],
        on_open_streaming: Callable[[], None],
    ) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.surface)
        self._controller = controller
        self._ui = ui
        self._after_id: str | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._status = tk.Label(
            self,
            text="RADIO",
            bg=ui.surface,
            fg=ui.accent_primary,
            font=("Sans", 9, "bold"),
            anchor="w",
        )
        self._status.grid(row=0, column=0, sticky="ew", padx=12, pady=(9, 0))

        source_shortcuts = tk.Frame(self, bg=ui.surface)
        source_shortcuts.grid(row=0, column=1, sticky="e", padx=(4, 10), pady=(7, 0))

        self._rf_button = tk.Button(
            source_shortcuts,
            text="⌁  RF",
            command=on_open_rf,
            bg=ui.surface,
            fg=ui.accent_success,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            font=("Sans", 8, "bold"),
            padx=6,
            pady=3,
        )
        self._rf_button.grid(row=0, column=0, padx=(0, 4))

        self._stream_button = tk.Button(
            source_shortcuts,
            text="◉  STREAM",
            command=on_open_streaming,
            bg=ui.surface,
            fg=ui.accent_primary,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            font=("Sans", 8, "bold"),
            padx=6,
            pady=3,
        )
        self._stream_button.grid(row=0, column=1)

        self._station = tk.Label(
            self,
            text="No radio active",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 16, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=500,
        )
        self._station.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=(2, 4))

        self._detail = tk.Label(
            self,
            text="Choose RF or streaming",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 9),
            anchor="w",
        )
        self._detail.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 9))

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
            self._status.configure(text="● STREAMING RADIO", fg=self._ui.accent_success)
            self._station.configure(text=current.name)
            details: list[str] = []
            if current.state:
                details.append(current.state)
            if current.codec:
                details.append(current.codec)
            if current.bitrate_kbps is not None:
                details.append(f"{current.bitrate_kbps} kbps")
            self._detail.configure(text=" • ".join(details) or "Streaming radio")
            self._stream_button.configure(fg=self._ui.accent_success)
        else:
            self._status.configure(text="RADIO", fg=self._ui.accent_primary)
            self._station.configure(text="No radio active")
            self._detail.configure(text="Choose RF or streaming")
            self._stream_button.configure(fg=self._ui.accent_primary)
        self._after_id = self.after(750, self._refresh)
