# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Embedded music-video presentation for the Spotify Tk screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.tk.media.spotify_services_if import (
    MusicVideoPresentationIf,
    MusicVideoRequestHandlerIf,
)
from frontends.x11 import X11WindowEmbedder

SPOTIFY_GREEN = "#1DB954"
MUSIC_VIDEO_WINDOW_CLASS = "OpenRoadCodeMusicVideo"


class SpotifyVideoOverlay:
    """Embed the active music-video browser over the Spotify content area."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        controller: MusicVideoRequestHandlerIf,
        presentation: MusicVideoPresentationIf,
        on_returned: Callable[[], None],
        set_status: Callable[[str], None],
    ) -> None:
        self._parent = parent
        self._controller = controller
        self._presentation = presentation
        self._on_returned = on_returned
        self._set_status = set_status
        self._embedder = X11WindowEmbedder()
        self._overlay: tk.Frame | None = None
        self._host: tk.Frame | None = None

    @property
    def visible(self) -> bool:
        return self._overlay is not None

    def sync(self) -> None:
        """Show or remove the embedded browser to match controller state."""
        if not self._controller.is_video_active():
            self.close()
            return
        if self.visible:
            return

        process_id = self._presentation.browser_process_id
        if process_id is None:
            return
        if not X11WindowEmbedder.supported():
            self._set_status("Music video is playing externally; xdotool is unavailable")
            return

        overlay = tk.Frame(self._parent, bg="#000000")
        overlay.place(x=0, y=0, relwidth=1, relheight=1)

        controls = tk.Frame(overlay, bg="#181818")
        controls.pack(fill=tk.X)
        tk.Label(
            controls,
            text="MUSIC VIDEO",
            bg="#181818",
            fg="#FFFFFF",
            font=("Sans", 10, "bold"),
        ).pack(side=tk.LEFT, padx=10, pady=7)
        tk.Button(
            controls,
            text="‹ RETURN TO SPOTIFY",
            command=self.return_to_spotify,
            bg=SPOTIFY_GREEN,
            fg="#000000",
            activebackground=SPOTIFY_GREEN,
            activeforeground="#000000",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=6, pady=4)

        host = tk.Frame(overlay, bg="#000000")
        host.pack(fill=tk.BOTH, expand=True)
        host.bind("<Configure>", self._on_resize)

        self._overlay = overlay
        self._host = host
        try:
            self._parent.update_idletasks()
            self._embedder.embed(
                process_id,
                int(host.winfo_id()),
                max(1, host.winfo_width()),
                max(1, host.winfo_height()),
                window_class=MUSIC_VIDEO_WINDOW_CLASS,
                window_name="YouTube Music Video",
            )
            overlay.lift()
            self._set_status("Spotify music video embedded")
        except Exception as error:
            self.close()
            self._set_status(f"Spotify video embed failed: {error}")

    def return_to_spotify(self) -> None:
        """Detach the browser and restore the saved Spotify state."""
        self.close()
        try:
            self._controller.return_to_spotify()
        except Exception as error:
            self._set_status(f"Return to Spotify failed: {error}")
            return
        self._set_status("Returned to Spotify")
        self._on_returned()

    def close(self) -> None:
        """Detach and destroy the overlay without changing playback state."""
        if self._embedder.window_id is not None:
            try:
                self._embedder.detach(int(self._parent.winfo_toplevel().winfo_id()))
            except (RuntimeError, tk.TclError):
                self._embedder.clear()

        overlay = self._overlay
        self._overlay = None
        self._host = None
        if overlay is not None:
            try:
                overlay.destroy()
            except tk.TclError:
                pass

    def _on_resize(self, event: tk.Event) -> None:
        if self._embedder.window_id is not None:
            self._embedder.resize(max(1, event.width), max(1, event.height))
