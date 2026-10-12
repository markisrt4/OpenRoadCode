# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Compact now-playing artwork using toolkit-independent preview requests."""

import io
import queue
import tkinter as tk
from PIL import Image, ImageTk
from ui.media.media_preview_if import MediaPreviewIf
from ui.media import PlaybackState


class MediaPreview(tk.Frame):
    def __init__(self, parent, *, handler: MediaPreviewIf, ui, on_open):
        super().__init__(parent, bg=ui.surface)
        self._handler = handler
        self._results = queue.SimpleQueue()
        self._closed = False
        self._url = None
        self._photo = None
        self._after = None
        self.grid_columnconfigure(1, weight=1)
        art_host = tk.Frame(self, width=56, height=56, bg=ui.surface_alt)
        art_host.grid(row=0, column=0, rowspan=3, padx=(0, 10))
        art_host.grid_propagate(False)
        self._art = tk.Label(art_host, text="♫", bg=ui.surface_alt, fg=ui.accent_success,
                             font=("Sans", 24, "bold"), bd=0)
        self._art.place(relwidth=1, relheight=1)
        self._caption = tk.Label(self, text="SPOTIFY", bg=ui.surface,
                                 fg=ui.accent_success, font=("Sans", 8, "bold"), anchor="w")
        self._caption.grid(row=0, column=1, sticky="ew")
        self._title = tk.Label(self, bg=ui.surface, fg=ui.text,
                               font=("Sans", 12, "bold"), anchor="w", width=1)
        self._title.grid(row=1, column=1, sticky="ew")
        self._artist = tk.Label(self, bg=ui.surface, fg=ui.text_muted,
                                font=("Sans", 9), anchor="w", width=1)
        self._artist.grid(row=2, column=1, sticky="ew")
        for widget in (self, art_host, self._art, self._caption, self._title, self._artist):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", lambda _event: on_open())
        self.bind("<Destroy>", self._destroyed, add="+")
        self._refresh()

    def _refresh(self):
        if self._closed:
            return
        state = self._handler.read_state()
        self._title.configure(text=state.title or "Your music, your device")
        self._artist.configure(text=state.artist or "Open Spotify to start listening")
        self._caption.configure(text="SPOTIFY · NOW PLAYING" if state.playback is PlaybackState.PLAYING
                                else "SPOTIFY · PAUSED" if state.title else "SPOTIFY")
        url = state.artwork_uri
        if url != self._url:
            self._url = url
            self._photo = None
            self._art.configure(image="", text="♫")
            if url:
                results = self._results
                self._handler.request_artwork(url, lambda data, key=url: results.put((key, data)))
        while not self._results.empty():
            key, data = self._results.get_nowait()
            if key == self._url and data:
                try:
                    with Image.open(io.BytesIO(data)) as image:
                        self._photo = ImageTk.PhotoImage(image)
                    self._art.configure(image=self._photo, text="")
                except (OSError, ValueError, tk.TclError):
                    pass
        self._after = self.after(500, self._refresh)

    def _destroyed(self, event):
        if event.widget is self:
            self.stop()

    def stop(self):
        """Stop preview polling on hide or destruction."""
        self._closed = True
        if self._after is not None:
            self.after_cancel(self._after)
            self._after = None
