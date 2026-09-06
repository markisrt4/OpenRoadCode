# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify playback destination and library navigation controls."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.spotify_local_player import SpotifyLocalPlayer, SpotifyPlaybackMode
from apps.orcUi.spotify_state_service import SpotifyStateService
from controllers.spotify.spotify_library import SpotifyLibraryTrack, SpotifyPlaylist

SPOTIFY_BG = "#121212"
SPOTIFY_SURFACE = "#181818"
SPOTIFY_SURFACE_HOVER = "#282828"
SPOTIFY_GREEN = "#1DB954"
SPOTIFY_MUTED = "#B3B3B3"
SPOTIFY_BORDER = "#303030"
TEXT = "#FFFFFF"


class SpotifyBrowsePanel(tk.Frame):
    """Compact Spotify mode and library browser for the integrated screen."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        service: SpotifyStateService,
        local_player: SpotifyLocalPlayer,
        dispatch_ui: Callable[[Callable[[], None]], None],
        show_now_playing: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=SPOTIFY_BG)
        self._service = service
        self._local_player = local_player
        self._dispatch_ui = dispatch_ui
        self._show_now_playing = show_now_playing
        self._content = tk.Frame(self, bg=SPOTIFY_BG)
        self._content.pack(fill=tk.BOTH, expand=True)
        self._mode_status: tk.Label | None = None
        self._mode_buttons: dict[SpotifyPlaybackMode, tk.Button] = {}
        self.show_home()

    def show_home(self) -> None:
        self._clear()
        self._build_mode_bar()
        self._build_browse_bar(active=None)
        self._empty_message("Choose a collection or return to now playing.")

    def show_saved(self) -> None:
        self._load_collection("LIKED SONGS", "liked", self._service.load_saved_tracks)

    def show_recent(self) -> None:
        self._load_collection("RECENTLY PLAYED", "recent", self._service.load_recently_played)

    def show_playlists(self) -> None:
        self._clear()
        self._build_mode_bar()
        self._build_browse_bar(active="playlists")
        self._loading("Loading playlists…")
        threading.Thread(target=self._load_playlists_worker, daemon=True, name="spotify-playlists").start()

    def _build_mode_bar(self) -> None:
        bar = tk.Frame(self._content, bg=SPOTIFY_BG)
        bar.pack(fill=tk.X, padx=4, pady=(0, 4))
        tk.Label(bar, text="PLAYBACK", bg=SPOTIFY_BG, fg=SPOTIFY_MUTED, font=("Sans", 8, "bold")).pack(side=tk.LEFT, padx=(8, 8), pady=5)
        self._mode_buttons = {}
        for mode, command in (
            (SpotifyPlaybackMode.REMOTE, self._local_player.request_remote),
            (SpotifyPlaybackMode.PLAYER, self._local_player.request_player),
        ):
            button = tk.Button(bar, text=mode.value, command=lambda c=command: self._change_mode(c), bg=SPOTIFY_SURFACE, fg=TEXT, activebackground=SPOTIFY_GREEN, activeforeground="#000000", relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=14, pady=5)
            button.pack(side=tk.LEFT, padx=2, pady=4)
            self._mode_buttons[mode] = button
        self._mode_status = tk.Label(bar, text="", bg=SPOTIFY_BG, fg=SPOTIFY_MUTED, font=("Sans", 9))
        self._mode_status.pack(side=tk.LEFT, padx=(10, 0))
        self._paint_mode()

    def _change_mode(self, command: Callable[[], None]) -> None:
        command()
        self.after(100, self._poll_mode)

    def _poll_mode(self) -> None:
        self._paint_mode()
        if self._local_player.state().busy:
            self.after(200, self._poll_mode)

    def _paint_mode(self) -> None:
        state = self._local_player.state()
        for mode, button in self._mode_buttons.items():
            selected = state.mode is mode
            button.configure(bg=SPOTIFY_GREEN if selected else SPOTIFY_SURFACE, fg="#000000" if selected else TEXT, state=tk.NORMAL if mode is SpotifyPlaybackMode.REMOTE or state.available else tk.DISABLED)
        if self._mode_status is not None:
            self._mode_status.configure(text=state.message)

    def _build_browse_bar(self, *, active: str | None) -> None:
        bar = tk.Frame(self._content, bg=SPOTIFY_BG)
        bar.pack(fill=tk.X, padx=4, pady=(0, 5))
        tk.Label(bar, text="BROWSE", bg=SPOTIFY_BG, fg=SPOTIFY_MUTED, font=("Sans", 8, "bold")).pack(side=tk.LEFT, padx=(8, 8), pady=6)
        for key, text, command in (
            ("now", "NOW PLAYING", self._show_now_playing),
            ("liked", "♥  LIKED", self.show_saved),
            ("recent", "RECENT", self.show_recent),
            ("playlists", "PLAYLISTS", self.show_playlists),
        ):
            selected = key == active
            tk.Button(bar, text=text, command=command, bg=SPOTIFY_GREEN if selected else SPOTIFY_SURFACE, fg="#000000" if selected else TEXT, activebackground=SPOTIFY_SURFACE_HOVER, activeforeground=TEXT, relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=10, pady=5).pack(side=tk.LEFT, padx=2, pady=4)
        tk.Button(bar, text="SEARCH · COMING SOON", state=tk.DISABLED, bg=SPOTIFY_SURFACE, fg=SPOTIFY_MUTED, disabledforeground=SPOTIFY_MUTED, relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=10, pady=5).pack(side=tk.LEFT, padx=2, pady=4)

    def _load_collection(self, title: str, active: str, loader: Callable[..., tuple[SpotifyLibraryTrack, ...]]) -> None:
        self._clear()
        self._build_mode_bar()
        self._build_browse_bar(active=active)
        self._loading(f"Loading {title.lower()}…")
        threading.Thread(target=self._load_tracks_worker, args=(title, active, loader), daemon=True, name=f"spotify-{active}").start()

    def _load_tracks_worker(self, title: str, active: str, loader: Callable[..., tuple[SpotifyLibraryTrack, ...]]) -> None:
        try:
            tracks = loader(limit=18)
            self._dispatch_ui(lambda: self._render_tracks(title, active, tracks))
        except Exception as error:
            self._dispatch_ui(lambda: self._render_error(str(error)))

    def _load_playlists_worker(self) -> None:
        try:
            playlists = self._service.load_playlists(limit=18)
            self._dispatch_ui(lambda: self._render_playlists(playlists))
        except Exception as error:
            self._dispatch_ui(lambda: self._render_error(str(error)))

    def _render_tracks(self, title: str, active: str, tracks: tuple[SpotifyLibraryTrack, ...]) -> None:
        self._clear()
        self._build_mode_bar()
        self._build_browse_bar(active=active)
        self._heading(title, f"{len(tracks)} tracks")
        grid = self._grid()
        for index, track in enumerate(tracks):
            card = self._item_card(grid, track.name, track.artist_name, command=lambda uri=track.uri: self._play_track(uri))
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=4, pady=4)

    def _render_playlists(self, playlists: tuple[SpotifyPlaylist, ...]) -> None:
        self._clear()
        self._build_mode_bar()
        self._build_browse_bar(active="playlists")
        self._heading("PLAYLISTS", f"{len(playlists)} playlists")
        grid = self._grid()
        for index, playlist in enumerate(playlists):
            detail = f"{playlist.item_count} tracks · {playlist.owner_name}"
            card = self._item_card(grid, playlist.name, detail, command=lambda item=playlist: self._open_playlist(item))
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=4, pady=4)

    def _open_playlist(self, playlist: SpotifyPlaylist) -> None:
        self._clear()
        self._build_mode_bar()
        self._build_browse_bar(active="playlists")
        self._loading(f"Loading {playlist.name}…")
        def worker() -> None:
            try:
                tracks = self._service.load_playlist_tracks(playlist.playlist_id, limit=18)
                self._dispatch_ui(lambda: self._render_tracks(playlist.name.upper(), "playlists", tracks))
            except Exception as error:
                self._dispatch_ui(lambda: self._render_error(str(error)))
        threading.Thread(target=worker, daemon=True, name="spotify-playlist-tracks").start()

    def _play_track(self, uri: str) -> None:
        self._service.request_play_track(uri)
        self._show_now_playing()

    def _grid(self) -> tk.Frame:
        grid = tk.Frame(self._content, bg=SPOTIFY_BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="spotify-items")
        return grid

    def _item_card(self, parent: tk.Misc, title: str, detail: str, *, command: Callable[[], None]) -> tk.Frame:
        card = tk.Frame(parent, bg=SPOTIFY_SURFACE, highlightthickness=1, highlightbackground=SPOTIFY_BORDER, height=72)
        card.grid_propagate(False)
        body = tk.Button(card, text=f"{title}\n{detail}", command=command, anchor="w", justify=tk.LEFT, bg=SPOTIFY_SURFACE, fg=TEXT, activebackground=SPOTIFY_SURFACE_HOVER, activeforeground=TEXT, relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=10, pady=8)
        body.pack(fill=tk.BOTH, expand=True)
        return card

    def _heading(self, title: str, detail: str) -> None:
        header = tk.Frame(self._content, bg=SPOTIFY_BG)
        header.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Label(header, text=title, bg=SPOTIFY_BG, fg=TEXT, font=("Sans", 14, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text=detail, bg=SPOTIFY_BG, fg=SPOTIFY_MUTED, font=("Sans", 9)).pack(side=tk.LEFT, padx=(10, 0))

    def _loading(self, text: str) -> None:
        self._empty_message(text)

    def _empty_message(self, text: str) -> None:
        tk.Label(self._content, text=text, bg=SPOTIFY_BG, fg=SPOTIFY_MUTED, font=("Sans", 12)).pack(expand=True)

    def _render_error(self, detail: str) -> None:
        self._clear()
        self._build_mode_bar()
        self._build_browse_bar(active=None)
        self._empty_message(f"Spotify: {detail}")

    def _clear(self) -> None:
        for child in self._content.winfo_children():
            child.destroy()
