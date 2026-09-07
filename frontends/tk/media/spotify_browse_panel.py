# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Spotify playback destination and library navigation controls."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageTk

from apps.orcUi.spotify_local_player import SpotifyLocalPlayer, SpotifyPlaybackMode
from apps.orcUi.spotify_state_service import SpotifyStateService
from controllers.spotify.spotify_library import SpotifyLibraryTrack, SpotifyPlaylist
from frontends.tk.media.spotify_services_if import ArtworkProviderIf

SPOTIFY_BG = "#121212"
SPOTIFY_SURFACE = "#181818"
SPOTIFY_SURFACE_HOVER = "#282828"
SPOTIFY_GREEN = "#1DB954"
SPOTIFY_MUTED = "#B3B3B3"
SPOTIFY_BORDER = "#303030"
TEXT = "#FFFFFF"
ART_SIZE = 56
LIBRARY_LIMIT = 18
LIBRARY_COLUMNS = 3


class SpotifyBrowsePanel(tk.Frame):
    """Spotify playback destination and library browser for the integrated UI."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        service: SpotifyStateService,
        local_player: SpotifyLocalPlayer,
        dispatch_ui: Callable[[Callable[[], None]], None],
        show_now_playing: Callable[[], None],
        image_cache: ArtworkProviderIf | None = None,
    ) -> None:
        super().__init__(parent, bg=SPOTIFY_BG)
        self._service = service
        self._local_player = local_player
        self._dispatch_ui = dispatch_ui
        self._show_now_playing = show_now_playing
        self._image_cache = image_cache
        self._images: list[ImageTk.PhotoImage] = []
        self._generation = 0
        self._content = tk.Frame(self, bg=SPOTIFY_BG)
        self._content.pack(fill=tk.BOTH, expand=True)
        self._mode_status: tk.Label | None = None
        self._mode_buttons: dict[SpotifyPlaybackMode, tk.Button] = {}
        self.show_home()

    def show_now_playing_header(self) -> None:
        self._replace_content()
        self._build_mode_bar()
        self._build_browse_bar(active="now")

    def show_home(self) -> None:
        self._begin_view()
        self._build_mode_bar()
        self._build_browse_bar(active=None)
        self._empty_message("Choose a collection or return to now playing.")

    def show_saved(self) -> None:
        self._load_collection(
            "LIKED SONGS",
            "liked",
            self._service.cached_saved_tracks,
            self._service.load_saved_tracks,
        )

    def show_recent(self) -> None:
        self._load_collection(
            "RECENTLY PLAYED",
            "recent",
            self._service.cached_recently_played,
            self._service.load_recently_played,
        )

    def show_playlists(self) -> None:
        generation = self._begin_view()
        cached = self._service.cached_playlists()
        if cached is not None:
            self._render_playlists(cached, generation)
            return
        self._build_collection_shell("PLAYLISTS", active="playlists")
        self._loading("Loading playlists…")
        threading.Thread(
            target=self._load_playlists_worker,
            args=(generation,),
            daemon=True,
            name="spotify-playlists",
        ).start()

    def _build_mode_bar(self) -> None:
        bar = tk.Frame(self._content, bg=SPOTIFY_BG)
        bar.pack(fill=tk.X, padx=4, pady=(0, 4))
        tk.Label(
            bar,
            text="PLAYBACK",
            bg=SPOTIFY_BG,
            fg=SPOTIFY_MUTED,
            font=("Sans", 8, "bold"),
        ).pack(side=tk.LEFT, padx=(8, 8), pady=5)

        self._mode_buttons = {}
        for mode, command in (
            (SpotifyPlaybackMode.REMOTE, self._local_player.request_remote),
            (SpotifyPlaybackMode.PLAYER, self._local_player.request_player),
        ):
            button = tk.Button(
                bar,
                text=mode.value,
                command=lambda c=command: self._change_mode(c),
                bg=SPOTIFY_SURFACE,
                fg=TEXT,
                activebackground=SPOTIFY_GREEN,
                activeforeground="#000000",
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9, "bold"),
                padx=14,
                pady=5,
                cursor="hand2",
            )
            button.pack(side=tk.LEFT, padx=2, pady=4)
            self._mode_buttons[mode] = button

        self._mode_status = tk.Label(
            bar,
            text="",
            bg=SPOTIFY_BG,
            fg=SPOTIFY_MUTED,
            font=("Sans", 9),
        )
        self._mode_status.pack(side=tk.LEFT, padx=(10, 0))
        self._paint_mode()

    def _change_mode(self, command: Callable[[], None]) -> None:
        command()
        self._service.request_refresh()
        self.after(100, self._poll_mode)

    def _poll_mode(self) -> None:
        self._paint_mode()
        if self._local_player.state().busy:
            self.after(200, self._poll_mode)

    def _paint_mode(self) -> None:
        state = self._local_player.state()
        for mode, button in self._mode_buttons.items():
            selected = state.mode is mode
            disabled = state.busy or (
                mode is SpotifyPlaybackMode.PLAYER and not state.available
            )
            button.configure(
                bg=SPOTIFY_GREEN if selected else SPOTIFY_SURFACE,
                fg="#000000" if selected else TEXT,
                state=tk.DISABLED if disabled else tk.NORMAL,
            )
        if self._mode_status is not None:
            self._mode_status.configure(
                text=state.message,
                fg=(
                    SPOTIFY_GREEN
                    if state.mode is SpotifyPlaybackMode.PLAYER and not state.busy
                    else SPOTIFY_MUTED
                ),
            )

    def _build_browse_bar(self, *, active: str | None) -> None:
        bar = tk.Frame(self._content, bg=SPOTIFY_BG)
        bar.pack(fill=tk.X, padx=4, pady=(0, 5))
        tk.Label(
            bar,
            text="BROWSE",
            bg=SPOTIFY_BG,
            fg=SPOTIFY_MUTED,
            font=("Sans", 8, "bold"),
        ).pack(side=tk.LEFT, padx=(8, 8), pady=6)

        for key, text, command in (
            ("now", "NOW PLAYING", self._show_now_playing),
            ("liked", "♥  LIKED", self.show_saved),
            ("recent", "RECENT", self.show_recent),
            ("playlists", "PLAYLISTS", self.show_playlists),
        ):
            selected = key == active
            tk.Button(
                bar,
                text=text,
                command=command,
                bg=SPOTIFY_GREEN if selected else SPOTIFY_SURFACE,
                fg="#000000" if selected else TEXT,
                activebackground=SPOTIFY_GREEN,
                activeforeground="#000000",
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9, "bold"),
                padx=10,
                pady=5,
                cursor="hand2",
            ).pack(side=tk.LEFT, padx=2, pady=4)

        tk.Button(
            bar,
            text="SEARCH · COMING SOON",
            state=tk.DISABLED,
            bg=SPOTIFY_BG,
            fg=SPOTIFY_MUTED,
            disabledforeground=SPOTIFY_MUTED,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 8, "bold"),
            padx=10,
            pady=5,
        ).pack(side=tk.LEFT, padx=(8, 2), pady=4)

    def _load_collection(
        self,
        title: str,
        active: str,
        cached_loader: Callable[[], tuple[SpotifyLibraryTrack, ...] | None],
        network_loader: Callable[..., tuple[SpotifyLibraryTrack, ...]],
    ) -> None:
        generation = self._begin_view()
        cached = cached_loader()
        if cached is not None:
            self._render_tracks(title, active, cached, generation)
            return

        self._build_collection_shell(title, active=active)
        self._loading(f"Loading {title.lower()}…")
        threading.Thread(
            target=self._load_tracks_worker,
            args=(title, active, network_loader, generation),
            daemon=True,
            name=f"spotify-{active}",
        ).start()

    def _load_tracks_worker(
        self,
        title: str,
        active: str,
        loader: Callable[..., tuple[SpotifyLibraryTrack, ...]],
        generation: int,
    ) -> None:
        try:
            tracks = loader(limit=LIBRARY_LIMIT)
            self._dispatch_ui(
                lambda: self._render_tracks(title, active, tracks, generation)
            )
        except Exception as error:
            self._dispatch_ui(
                lambda: self._render_error(str(error), generation)
            )

    def _load_playlists_worker(self, generation: int) -> None:
        try:
            playlists = self._service.load_playlists(limit=LIBRARY_LIMIT)
            self._dispatch_ui(
                lambda: self._render_playlists(playlists, generation)
            )
        except Exception as error:
            self._dispatch_ui(
                lambda: self._render_error(str(error), generation)
            )

    def _render_tracks(
        self,
        title: str,
        active: str,
        tracks: tuple[SpotifyLibraryTrack, ...],
        generation: int,
        *,
        back_to_playlists: bool = False,
    ) -> None:
        if generation != self._generation:
            return
        self._replace_content()
        self._build_collection_shell(
            title,
            active=active,
            back_to_playlists=back_to_playlists,
        )
        self._heading(title, f"{len(tracks)} tracks")
        grid = self._grid()
        if not tracks:
            self._empty_message("No tracks returned.")
            return
        for index, track in enumerate(tracks[:LIBRARY_LIMIT]):
            self._track_card(grid, track, generation).grid(
                row=index // LIBRARY_COLUMNS,
                column=index % LIBRARY_COLUMNS,
                sticky="nsew",
                padx=4,
                pady=4,
            )

    def _render_playlists(
        self,
        playlists: tuple[SpotifyPlaylist, ...],
        generation: int,
    ) -> None:
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
            self._playlist_card(grid, playlist, generation).grid(
                row=index // LIBRARY_COLUMNS,
                column=index % LIBRARY_COLUMNS,
                sticky="nsew",
                padx=4,
                pady=4,
            )

    def _build_collection_shell(
        self,
        title: str,
        *,
        active: str,
        back_to_playlists: bool = False,
    ) -> None:
        self._build_mode_bar()
        toolbar = tk.Frame(self._content, bg=SPOTIFY_BG)
        toolbar.pack(fill=tk.X, padx=4, pady=(0, 2))
        tk.Button(
            toolbar,
            text="‹ PLAYLISTS" if back_to_playlists else "‹ NOW PLAYING",
            command=self.show_playlists if back_to_playlists else self._show_now_playing,
            bg=SPOTIFY_SURFACE,
            fg=TEXT,
            activebackground=SPOTIFY_SURFACE_HOVER,
            activeforeground=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(4, 8), pady=4)
        tk.Label(
            toolbar,
            text=title,
            bg=SPOTIFY_BG,
            fg=TEXT,
            font=("Sans", 13, "bold"),
        ).pack(side=tk.LEFT, pady=4)
        tk.Label(
            toolbar,
            text="  SPOTIFY",
            bg=SPOTIFY_BG,
            fg=SPOTIFY_GREEN,
            font=("Sans", 8, "bold"),
        ).pack(side=tk.LEFT, pady=4)
        self._build_browse_bar(active=active)

    def _track_card(
        self,
        parent: tk.Misc,
        track: SpotifyLibraryTrack,
        generation: int,
    ) -> tk.Frame:
        detail = track.artist_name
        if track.album_name:
            detail += f"  •  {track.album_name}"
        return self._art_card(
            parent,
            track.name,
            detail,
            track.album_art_url,
            lambda: self._play_track(track.uri),
            generation,
        )

    def _playlist_card(
        self,
        parent: tk.Misc,
        playlist: SpotifyPlaylist,
        generation: int,
    ) -> tk.Frame:
        detail = f"{playlist.item_count or 0} tracks"
        if playlist.owner_name:
            detail += f"  •  {playlist.owner_name}"
        return self._art_card(
            parent,
            playlist.name,
            detail,
            playlist.image_url,
            lambda: self._open_playlist(playlist),
            generation,
        )

    def _art_card(
        self,
        parent: tk.Misc,
        title_text: str,
        detail_text: str,
        artwork_url: str | None,
        command: Callable[[], None],
        generation: int,
    ) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=SPOTIFY_SURFACE,
            highlightthickness=1,
            highlightbackground=SPOTIFY_BORDER,
            cursor="hand2",
            height=76,
        )
        card.grid_propagate(False)
        card.grid_columnconfigure(1, weight=1)

        art_host = tk.Frame(card, bg=SPOTIFY_SURFACE)
        art_host.grid(row=0, column=0, rowspan=2, padx=7, pady=7)
        art = tk.Label(
            art_host,
            text="♫",
            bg="#242424",
            fg=SPOTIFY_GREEN,
            font=("Sans", 18, "bold"),
            width=5,
            height=2,
        )
        art.pack()
        loading = tk.Label(
            art_host,
            text="LOADING" if artwork_url else "",
            bg=SPOTIFY_SURFACE,
            fg=SPOTIFY_MUTED,
            font=("Sans", 6, "bold"),
        )
        loading.pack(pady=(1, 0))

        title = tk.Label(
            card,
            text=title_text,
            bg=SPOTIFY_SURFACE,
            fg=TEXT,
            font=("Sans", 9, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=150,
        )
        title.grid(row=0, column=1, sticky="sew", padx=(0, 7), pady=(7, 0))
        detail = tk.Label(
            card,
            text=detail_text,
            bg=SPOTIFY_SURFACE,
            fg=SPOTIFY_MUTED,
            font=("Sans", 8),
            anchor="w",
            justify=tk.LEFT,
            wraplength=155,
        )
        detail.grid(row=1, column=1, sticky="new", padx=(0, 7), pady=(1, 7))

        widgets = (card, art_host, art, loading, title, detail)
        for widget in widgets:
            widget.bind("<Button-1>", lambda _event, c=command: c())
        self._bind_hover(card, widgets[1:])
        if artwork_url and self._image_cache is not None:
            self._load_artwork(artwork_url, art, loading, generation)
        return card

    def _load_artwork(
        self,
        url: str,
        label: tk.Label,
        loading: tk.Label,
        generation: int,
    ) -> None:
        def worker() -> None:
            try:
                image = (
                    self._image_cache.get(url, width=ART_SIZE, height=ART_SIZE)
                    if self._image_cache is not None
                    else None
                )
            except Exception:
                image = None
            self._dispatch_ui(
                lambda: self._apply_artwork(label, loading, image, generation)
            )

        threading.Thread(
            target=worker,
            daemon=True,
            name="spotify-library-art",
        ).start()

    def _apply_artwork(
        self,
        label: tk.Label,
        loading: tk.Label,
        image: Image.Image | None,
        generation: int,
    ) -> None:
        try:
            if generation != self._generation or not label.winfo_exists():
                if image is not None:
                    image.close()
                return
            if loading.winfo_exists():
                loading.configure(text="")
            if image is None:
                return
            photo = ImageTk.PhotoImage(image)
            image.close()
            self._images.append(photo)
            label.configure(
                image=photo,
                text="",
                width=ART_SIZE,
                height=ART_SIZE,
            )
        except tk.TclError:
            if image is not None:
                image.close()

    @staticmethod
    def _bind_hover(card: tk.Frame, children: tuple[tk.Widget, ...]) -> None:
        def enter(_event=None) -> None:
            try:
                card.configure(
                    bg=SPOTIFY_SURFACE_HOVER,
                    highlightbackground=SPOTIFY_GREEN,
                )
                for widget in children:
                    if widget.cget("bg") == SPOTIFY_SURFACE:
                        widget.configure(bg=SPOTIFY_SURFACE_HOVER)
            except tk.TclError:
                pass

        def leave(_event=None) -> None:
            try:
                card.configure(
                    bg=SPOTIFY_SURFACE,
                    highlightbackground=SPOTIFY_BORDER,
                )
                for widget in children:
                    if widget.cget("bg") == SPOTIFY_SURFACE_HOVER:
                        widget.configure(bg=SPOTIFY_SURFACE)
            except tk.TclError:
                pass

        card.bind("<Enter>", enter)
        card.bind("<Leave>", leave)
        for widget in children:
            widget.bind("<Enter>", enter, add="+")
            widget.bind("<Leave>", leave, add="+")

    def _open_playlist(self, playlist: SpotifyPlaylist) -> None:
        generation = self._begin_view()
        self._build_collection_shell(
            playlist.name.upper(),
            active="playlists",
            back_to_playlists=True,
        )
        self._loading(f"Loading {playlist.name}…")

        def worker() -> None:
            try:
                tracks = self._service.load_playlist_tracks(
                    playlist.playlist_id,
                    limit=LIBRARY_LIMIT,
                )
                self._dispatch_ui(
                    lambda: self._render_tracks(
                        playlist.name.upper(),
                        "playlists",
                        tracks,
                        generation,
                        back_to_playlists=True,
                    )
                )
            except Exception as error:
                self._dispatch_ui(
                    lambda: self._render_error(str(error), generation)
                )

        threading.Thread(
            target=worker,
            daemon=True,
            name="spotify-playlist-tracks",
        ).start()

    def _play_track(self, uri: str) -> None:
        self._service.request_play_track(uri)
        self._service.request_refresh()
        self._show_now_playing()

    def _grid(self) -> tk.Frame:
        grid = tk.Frame(self._content, bg=SPOTIFY_BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        for column in range(LIBRARY_COLUMNS):
            grid.grid_columnconfigure(
                column,
                weight=1,
                uniform="spotify-items",
            )
        return grid

    def _heading(self, title: str, detail: str) -> None:
        header = tk.Frame(self._content, bg=SPOTIFY_BG)
        header.pack(fill=tk.X, padx=10, pady=(2, 4))
        tk.Label(
            header,
            text=title,
            bg=SPOTIFY_BG,
            fg=TEXT,
            font=("Sans", 14, "bold"),
        ).pack(side=tk.LEFT)
        tk.Label(
            header,
            text=detail,
            bg=SPOTIFY_BG,
            fg=SPOTIFY_MUTED,
            font=("Sans", 9),
        ).pack(side=tk.LEFT, padx=(10, 0))

    def _loading(self, text: str) -> None:
        self._empty_message(text)

    def _empty_message(self, text: str) -> None:
        tk.Label(
            self._content,
            text=text,
            bg=SPOTIFY_BG,
            fg=SPOTIFY_MUTED,
            font=("Sans", 12),
        ).pack(expand=True)

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
        for child in self._content.winfo_children():
            child.destroy()
