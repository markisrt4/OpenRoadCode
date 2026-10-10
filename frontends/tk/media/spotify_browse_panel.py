# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify playback destination and library navigation controls."""

from __future__ import annotations

import io
from functools import partial
import tkinter as tk
from collections.abc import Callable
from typing import Any

from PIL import Image, ImageOps, ImageTk

from ui.media.spotify_library import (SpotifyLibraryTrack, SpotifyPlaylist)
from ui.media.spotify_browse_if import (
    SpotifyBrowseRequests, SpotifyBrowseState, SpotifyCollection, SpotifyPlaybackMode,
)
from ui.ui_widget import UiWidget

ART_SIZE = 56
LIBRARY_LIMIT = 18
LIBRARY_COLUMNS = 3


class SpotifyBrowsePanel(tk.Frame, UiWidget):
    """Spotify playback destination and library browser for the integrated UI."""

    def __init__(
        self, parent: tk.Misc, *, show_now_playing: Callable[[], None],
        theme: dict[str, Any],
    ) -> None:
        self._colors = theme["colors"]
        self._show_now_playing = show_now_playing
        self._handler: SpotifyBrowseRequests | None = None
        self._state = SpotifyBrowseState()
        self._content_key: tuple[object, ...] | None = None
        self._art_labels: dict[str, list[tuple[tk.Label, tk.Label]]] = {}
        self._images: list[ImageTk.PhotoImage] = []
        self._generation = 0
        super().__init__(parent, bg=self._color("background"))
        self._content = tk.Frame(self, bg=self._color("background"))
        self._content.pack(fill=tk.BOTH, expand=True)
        self._mode_status: tk.Label | None = None
        self._mode_buttons: dict[SpotifyPlaybackMode, tk.Button] = {}

    def _color(self, key: str) -> str:
        return str(self._colors[key])

    def _button(self, parent: tk.Misc, text: str, command: Callable[[], None], *, selected: bool = False, padx: int = 10, pady: int = 5) -> tk.Button:
        c = self._color
        return tk.Button(parent, text=text, command=command,
            bg=c("button_active_background") if selected else c("button_background"),
            fg=c("button_active_foreground") if selected else c("button_foreground"),
            activebackground=c("button_active_background"), activeforeground=c("button_active_foreground"),
            relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=padx, pady=pady, cursor="hand2")

    def set_browse_request_handler(self, handler: SpotifyBrowseRequests | None) -> None:
        self._handler = handler

    def set_browse_state(self, state: SpotifyBrowseState) -> None:
        self._state = state
        key = (state.collection, state.title, state.tracks, state.playlists, state.loading, state.message)
        if key != self._content_key:
            self._content_key = key
            self._begin_view()
            collection = state.collection
            if collection in (SpotifyCollection.NOW, SpotifyCollection.HOME):
                self._build_mode_bar()
                self._build_browse_bar(active="now" if collection is SpotifyCollection.NOW else None)
                if collection is SpotifyCollection.HOME:
                    self._empty_message("Choose a collection or return to now playing.")
            elif state.loading or state.message:
                self._build_collection_shell(state.title, active=collection.value,
                    back_to_playlists=collection is SpotifyCollection.PLAYLIST)
                self._empty_message(state.message or f"Loading {state.title.lower()}…")
            elif collection is SpotifyCollection.PLAYLISTS:
                self._render_playlists(state.playlists, self._generation)
            else:
                self._render_tracks(state.title, "playlists" if collection is SpotifyCollection.PLAYLIST else collection.value,
                    state.tracks, self._generation, back_to_playlists=collection is SpotifyCollection.PLAYLIST)
        self._paint_mode()

    def _request_collection(self, collection: SpotifyCollection) -> None:
        if self._handler is not None:
            self._handler.request_collection(collection)

    def show_now_playing_header(self) -> None:
        self._request_collection(SpotifyCollection.NOW)

    def show_home(self) -> None:
        self._request_collection(SpotifyCollection.HOME)

    def show_saved(self) -> None:
        self._request_collection(SpotifyCollection.LIKED)

    def show_recent(self) -> None:
        self._request_collection(SpotifyCollection.RECENT)

    def show_playlists(self) -> None:
        self._request_collection(SpotifyCollection.PLAYLISTS)

    def _build_mode_bar(self) -> None:
        c = self._color
        bar = tk.Frame(self._content, bg=c("background"))
        bar.pack(fill=tk.X, padx=4, pady=(0, 4))
        tk.Label(bar, text="PLAYBACK", bg=c("background"), fg=c("detail"), font=("Sans", 8, "bold")).pack(side=tk.LEFT, padx=(8, 8), pady=5)
        self._mode_buttons = {}
        for mode in SpotifyPlaybackMode:
            button = self._button(bar, mode.value, partial(self._change_mode, mode), padx=14)
            button.pack(side=tk.LEFT, padx=2, pady=4)
            self._mode_buttons[mode] = button
        self._mode_status = tk.Label(bar, text="", bg=c("background"), fg=c("detail"), font=("Sans", 9))
        self._mode_status.pack(side=tk.LEFT, padx=(10, 0))
        self._paint_mode()

    def _change_mode(self, mode: SpotifyPlaybackMode) -> None:
        if self._handler is not None:
            self._handler.request_playback_mode(mode)

    def _paint_mode(self) -> None:
        c = self._color
        state = self._state.player
        for mode, button in self._mode_buttons.items():
            selected = state.mode is mode
            disabled = state.busy or (mode is SpotifyPlaybackMode.PLAYER and not state.available)
            button.configure(bg=c("button_active_background") if selected else c("button_background"),
                fg=c("button_active_foreground") if selected else c("button_foreground"),
                state=tk.DISABLED if disabled else tk.NORMAL)
        if self._mode_status is not None:
            self._mode_status.configure(text=self._state.message or state.message, fg=c("status") if state.mode is SpotifyPlaybackMode.PLAYER and not state.busy else c("detail"))

    def _build_browse_bar(self, *, active: str | None) -> None:
        c = self._color
        bar = tk.Frame(self._content, bg=c("background"))
        bar.pack(fill=tk.X, padx=4, pady=(0, 5))
        tk.Label(bar, text="BROWSE", bg=c("background"), fg=c("detail"), font=("Sans", 8, "bold")).pack(side=tk.LEFT, padx=(8, 8), pady=6)
        for key, text, command in (("now", "NOW PLAYING", self._show_now_playing), ("liked", "♥  LIKED", self.show_saved), ("recent", "RECENT", self.show_recent), ("playlists", "PLAYLISTS", self.show_playlists)):
            self._button(bar, text, command, selected=key == active).pack(side=tk.LEFT, padx=2, pady=4)
        tk.Button(bar, text="SEARCH · COMING SOON", state=tk.DISABLED, bg=c("background"), fg=c("detail"), disabledforeground=c("detail"), relief=tk.FLAT, bd=0, font=("Sans", 8, "bold"), padx=10, pady=5).pack(side=tk.LEFT, padx=(8, 2), pady=4)

    def _render_tracks(self, title: str, active: str, tracks: tuple[SpotifyLibraryTrack, ...], generation: int, *, back_to_playlists: bool = False) -> None:
        if generation != self._generation:
            return
        self._replace_content()
        self._build_collection_shell(title, active=active, back_to_playlists=back_to_playlists)
        self._heading(title, f"{len(tracks)} tracks")
        grid = self._grid()
        if not tracks:
            self._empty_message("No tracks returned.")
            return
        for index, track in enumerate(tracks[:LIBRARY_LIMIT]):
            self._track_card(grid, track, generation).grid(row=index // LIBRARY_COLUMNS, column=index % LIBRARY_COLUMNS, sticky="nsew", padx=4, pady=4)

    def _render_playlists(self, playlists: tuple[SpotifyPlaylist, ...], generation: int) -> None:
        if generation != self._generation:
            return
        self._replace_content()
        self._build_collection_shell("PLAYLISTS", active="playlists")
        self._heading("PLAYLISTS", f"{len(playlists)} playlists")
        grid = self._grid()
        if not playlists:
            self._empty_message("No playlists returned.")
            return
        for index, playlist in enumerate(playlists[:LIBRARY_LIMIT]):
            self._playlist_card(grid, playlist, generation).grid(row=index // LIBRARY_COLUMNS, column=index % LIBRARY_COLUMNS, sticky="nsew", padx=4, pady=4)

    def _build_collection_shell(self, title: str, *, active: str, back_to_playlists: bool = False) -> None:
        c = self._color
        self._build_mode_bar()
        toolbar = tk.Frame(self._content, bg=c("background"))
        toolbar.pack(fill=tk.X, padx=4, pady=(0, 2))
        self._button(toolbar, "‹ PLAYLISTS" if back_to_playlists else "‹ NOW PLAYING", self.show_playlists if back_to_playlists else self._show_now_playing).pack(side=tk.LEFT, padx=(4, 8), pady=4)
        tk.Label(toolbar, text=title, bg=c("background"), fg=c("title"), font=("Sans", 13, "bold")).pack(side=tk.LEFT, pady=4)
        tk.Label(toolbar, text="  SPOTIFY", bg=c("background"), fg=c("status"), font=("Sans", 8, "bold")).pack(side=tk.LEFT, pady=4)
        self._build_browse_bar(active=active)

    def _track_card(self, parent: tk.Misc, track: SpotifyLibraryTrack, generation: int) -> tk.Frame:
        detail = track.artist_name
        if track.album_name:
            detail += f"  •  {track.album_name}"
        return self._art_card(parent, track.name, detail, track.album_art_url, lambda: self._play_track(track.uri), generation)

    def _playlist_card(self, parent: tk.Misc, playlist: SpotifyPlaylist, generation: int) -> tk.Frame:
        detail = f"{playlist.item_count or 0} tracks"
        if playlist.owner_name:
            detail += f"  •  {playlist.owner_name}"
        return self._art_card(parent, playlist.name, detail, playlist.image_url, lambda: self._open_playlist(playlist), generation)

    def _art_card(self, parent: tk.Misc, title_text: str, detail_text: str, artwork_url: str | None, command: Callable[[], None], generation: int) -> tk.Frame:
        c = self._color
        card = tk.Frame(parent, bg=c("card_background"), highlightthickness=1, highlightbackground=c("card_border"), cursor="hand2", height=76)
        card.grid_propagate(False)
        card.grid_columnconfigure(1, weight=1)
        art_host = tk.Frame(card, bg=c("card_background"))
        art_host.grid(row=0, column=0, rowspan=2, padx=7, pady=7)
        art = tk.Label(art_host, text="♫", bg=c("button_background"), fg=c("status"), font=("Sans", 18, "bold"), width=5, height=2)
        art.pack()
        loading = tk.Label(art_host, text="LOADING" if artwork_url else "", bg=c("card_background"), fg=c("detail"), font=("Sans", 6, "bold"))
        loading.pack(pady=(1, 0))
        title = tk.Label(card, text=title_text, bg=c("card_background"), fg=c("title"), font=("Sans", 9, "bold"), anchor="w", justify=tk.LEFT, wraplength=150)
        title.grid(row=0, column=1, sticky="sew", padx=(0, 7), pady=(7, 0))
        detail = tk.Label(card, text=detail_text, bg=c("card_background"), fg=c("detail"), font=("Sans", 8), anchor="w", justify=tk.LEFT, wraplength=155)
        detail.grid(row=1, column=1, sticky="new", padx=(0, 7), pady=(1, 7))
        widgets = (card, art_host, art, loading, title, detail)
        for widget in widgets:
            widget.bind("<Button-1>", lambda _event: command())
        self._bind_hover(card, widgets[1:])
        if artwork_url:
            self._art_labels.setdefault(artwork_url, []).append((art, loading))
        return card

    def set_browse_artwork(self, uri: str, payload: bytes | None) -> None:
        for label, loading in self._art_labels.get(uri, ()):
            loading.configure(text="")
            if payload is None:
                continue
            try:
                with Image.open(io.BytesIO(payload)) as source:
                    image = ImageOps.fit(source, (ART_SIZE, ART_SIZE))
                    try:
                        photo = ImageTk.PhotoImage(image)
                    finally:
                        image.close()
                self._images.append(photo)
                label.configure(image=photo, text="", width=ART_SIZE, height=ART_SIZE)
            except (OSError, ValueError):
                pass

    def _bind_hover(self, card: tk.Frame, children: tuple[tk.Widget, ...]) -> None:
        c = self._color
        def enter(_event: tk.Event | None = None) -> None:
            try:
                card.configure(bg=c("button_background"), highlightbackground=c("status"))
                for widget in children:
                    if widget.cget("bg") == c("card_background"):
                        widget.configure({"bg": c("button_background")})
            except tk.TclError:
                pass
        def leave(_event: tk.Event | None = None) -> None:
            try:
                card.configure(bg=c("card_background"), highlightbackground=c("card_border"))
                for widget in children:
                    if widget.cget("bg") == c("button_background"):
                        widget.configure({"bg": c("card_background")})
            except tk.TclError:
                pass
        card.bind("<Enter>", enter)
        card.bind("<Leave>", leave)
        for widget in children:
            widget.bind("<Enter>", enter, add="+")
            widget.bind("<Leave>", leave, add="+")

    def _open_playlist(self, playlist: SpotifyPlaylist) -> None:
        if self._handler is not None:
            self._handler.request_playlist(playlist.playlist_id)

    def _play_track(self, uri: str) -> None:
        if self._handler is not None:
            self._handler.request_play_track(uri)

    def _grid(self) -> tk.Frame:
        grid = tk.Frame(self._content, bg=self._color("background"))
        grid.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        for column in range(LIBRARY_COLUMNS):
            grid.grid_columnconfigure(column, weight=1, uniform="spotify-items")
        return grid

    def _heading(self, title: str, detail: str) -> None:
        c = self._color
        header = tk.Frame(self._content, bg=c("background"))
        header.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Label(header, text=title, bg=c("background"), fg=c("title"), font=("Sans", 14, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text=detail, bg=c("background"), fg=c("detail"), font=("Sans", 9)).pack(side=tk.LEFT, padx=(10, 0))

    def _loading(self, text: str) -> None:
        self._empty_message(text)

    def _empty_message(self, text: str) -> None:
        tk.Label(self._content, text=text, bg=self._color("background"), fg=self._color("detail"), font=("Sans", 12)).pack(expand=True)

    def _render_error(self, detail: str, generation: int) -> None:
        if generation != self._generation:
            return
        self._replace_content()
        self._build_mode_bar()
        self._build_browse_bar(active=None)
        self._empty_message(f"Spotify: {detail}")

    def _begin_view(self) -> int:
        self._generation += 1
        self._replace_content()
        return self._generation

    def _replace_content(self) -> None:
        self._images.clear()
        self._art_labels.clear()
        for child in self._content.winfo_children():
            child.destroy()
