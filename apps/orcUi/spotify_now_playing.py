# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact Spotify now-playing summary for the ORC home screen."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from PIL import ImageTk

from apps.orcUi.orc_theme import DARK
from apps.orcUi.spotify_state_service import SpotifyStateService
from controllers.image import ImageCache
from ui.media import PlaybackState

PANEL = DARK["panel"]
TEXT = DARK["text"]
MUTED = DARK["muted"]
GREEN = "#84ce1f"
ART_SIZE = 76


class SpotifyNowPlaying(tk.Frame):
    """Render shared Spotify state and cached artwork without network work in Tk."""

    def __init__(self,parent:tk.Widget,*,service:SpotifyStateService,on_open:Callable[[],None])->None:
        super().__init__(parent,bg=PANEL,cursor="hand2")
        self._service=service; self._on_open=on_open; self._closed=False
        self._title=tk.StringVar(value="Spotify • YouTube • Netflix"); self._artist=tk.StringVar(value="Media hub"); self._status=tk.StringVar(value="")
        self._artwork_uri:str|None=None; self._artwork_photo:ImageTk.PhotoImage|None=None; self._art_results:queue.SimpleQueue[tuple[str,object|None]]=queue.SimpleQueue()
        cache_dir=Path.home()/".cache"/"openroadcode"/"spotify-artwork"
        self._image_cache=ImageCache(max_entries=16,cache_directory=cache_dir)
        body=tk.Frame(self,bg=PANEL); body.pack(fill=tk.BOTH,expand=True,padx=12,pady=8)
        self._art_label=tk.Label(body,text="♫",fg=GREEN,bg=DARK["active"],font=("Sans",24,"bold"),width=4,height=3); self._art_label.pack(side=tk.LEFT,padx=(0,12))
        text=tk.Frame(body,bg=PANEL); text.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        tk.Label(text,textvariable=self._title,fg=TEXT,bg=PANEL,font=("Sans",13,"bold"),anchor="w").pack(fill=tk.X,pady=(5,1)); tk.Label(text,textvariable=self._artist,fg=MUTED,bg=PANEL,font=("Sans",9),anchor="w").pack(fill=tk.X); tk.Label(text,textvariable=self._status,fg=GREEN,bg=PANEL,font=("Sans",8,"bold"),anchor="w").pack(fill=tk.X,pady=(3,0))
        self._bind_open(self); self._refresh()

    def destroy(self)->None:self._closed=True; super().destroy()
    def _bind_open(self,widget:tk.Widget)->None:
        widget.bind("<Button-1>",lambda _event:self._on_open())
        for child in widget.winfo_children():self._bind_open(child)

    def _refresh(self)->None:
        if self._closed:return
        self._apply_artwork_result(); state=self._service.latest_state()
        if state.playback is PlaybackState.PLAYING and state.title:
            self._title.set(state.title); self._artist.set(state.artist or ""); self._status.set("Spotify • Playing")
            if state.artwork_uri and state.artwork_uri!=self._artwork_uri:self._load_artwork(state.artwork_uri)
        else:
            self._title.set("Spotify • YouTube • Netflix"); self._artist.set("Media hub"); self._status.set(""); self._show_artwork_placeholder()
        self.after(500,self._refresh)

    def _load_artwork(self,uri:str)->None:
        self._artwork_uri=uri
        def worker()->None:
            try:image=self._image_cache.get(uri,width=ART_SIZE,height=ART_SIZE)
            except Exception:image=None
            self._art_results.put((uri,image))
        threading.Thread(target=worker,name="orcui-home-artwork",daemon=True).start()

    def _apply_artwork_result(self)->None:
        while True:
            try:uri,image=self._art_results.get_nowait()
            except queue.Empty:return
            if uri!=self._artwork_uri or image is None:continue
            self._artwork_photo=ImageTk.PhotoImage(image)
            self._art_label.configure(image=self._artwork_photo,text="",width=ART_SIZE,height=ART_SIZE)

    def _show_artwork_placeholder(self)->None:
        self._artwork_uri=None; self._artwork_photo=None; self._art_label.configure(image="",text="♫",width=4,height=3)
