# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Home-screen radio summary with streaming playback awareness."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.radio.streaming_radio_state_source_if import StreamingRadioStateSourceIf
from ui.theme import ThemeBundle
from ui.music_visualizer.home_spectrum_ui_if import HomeSpectrumFeedIf
from frontends.tk.media.home_spectrum_strip import HomeSpectrumStrip
from ui.ui_widget import UiWidget


class StreamingRadioNowPlaying(tk.Frame, UiWidget):
    """Present neutral radio state and current streaming playback on Home."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        state_source: StreamingRadioStateSourceIf,
        theme: ThemeBundle,
        on_open_rf: Callable[[], None],
        on_open_streaming: Callable[[], None],
        on_open_adsb: Callable[[], None],
        online_allowed: Callable[[], bool] = lambda: True,
    ) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.surface)
        self._online_allowed = online_allowed
        self._state_source = state_source
        self._ui = ui
        self._after_id: str | None = None
        self._spectrum: HomeSpectrumStrip | None = None

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

        source_shortcuts = tk.Frame(self, bg=ui.surface)
        source_shortcuts.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 8))
        source_shortcuts.grid_columnconfigure(0, weight=1, uniform="home-radio-actions")
        source_shortcuts.grid_columnconfigure(1, weight=1, uniform="home-radio-actions")

        self._rf_button = tk.Button(
            source_shortcuts,
            text="⌁  RF RADIO",
            command=on_open_rf,
            bg=ui.control_background,
            fg=ui.accent_success,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            font=("Sans", 11, "bold"),
            padx=8,
            pady=12,
        )
        self._rf_button.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self._stream_button = tk.Button(
            source_shortcuts,
            text="◉  STREAMING",
            command=on_open_streaming,
            bg=ui.control_background,
            fg=ui.accent_primary,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            font=("Sans", 11, "bold"),
            padx=8,
            pady=12,
        )
        self._stream_button.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        self._station = tk.Label(
            self,
            text="No radio active",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 16, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=260,
        )
        self._station.grid(row=1, column=0, columnspan=2, sticky="new", padx=12, pady=(6, 4))

        self._detail = tk.Label(
            self,
            text="Choose RF or streaming",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 9),
            anchor="w",
        )
        self._detail.grid(row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 4))

        self.bind("<Configure>", lambda event: self._station.configure(wraplength=max(1, event.width - 24)))
        self._refresh()

    def set_spectrum(self, feed: HomeSpectrumFeedIf, *, on_open: Callable[[], None]) -> None:
        """Use Radio's spare middle row for the shared Home audio spectrum."""
        if self._spectrum is not None:
            self._spectrum.destroy()
        self._spectrum = HomeSpectrumStrip(self, feed=feed,
            background=self._ui.surface, on_open=on_open)
        self._spectrum.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 2))

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
        online = self._online_allowed()
        self._stream_button.configure(state=tk.NORMAL if online else tk.DISABLED,
                                      disabledforeground=self._ui.text_muted)
        state = self._state_source.snapshot()
        current = state.station
        playing = current is not None and state.is_playing
        if playing and current is not None:
            self._status.grid(row=0, column=0, sticky="ew", padx=12, pady=(3, 0))
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
            self._status.grid_remove()
            self._status.configure(text="RADIO", fg=self._ui.accent_primary)
            self._station.configure(text="No radio active")
            self._detail.configure(text="Choose RF or streaming" if online else "Offline mode • RF available")
            self._stream_button.configure(fg=self._ui.accent_primary)
        self._after_id = self.after(750, self._refresh)
