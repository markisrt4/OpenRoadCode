"""Inline Spotify view for the Trending radio screen."""

import tkinter as tk
from collections.abc import Callable
from time import monotonic

from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel
from ui.media.spotify_browse_if import SpotifyLocalPlayerState, SpotifyPlaybackMode


def build_trending_spotify_pane(
    parent: tk.Misc,
    on_back: Callable[[], None],
    artist: str,
    title: str,
    *,
    theme: dict,
    activate: Callable[[SpotifyPlaybackPanel], Callable[[], None]],
    show_error: Callable[[str, str], None],
    dispatch_ui: Callable[[Callable[[], None]], None],
    android: bool,
    network_allowed: Callable[[], bool],
    request_song: Callable[[str, str, Callable[[str], None], Callable[[str], None]], None],
    player_state: Callable[[], SpotifyLocalPlayerState],
    request_player: Callable[[], None],
    configured: bool,
    on_setup: Callable[[], None],
) -> tk.Widget:
    colors = theme["colors"]
    host = tk.Frame(parent, bg=colors["background"])
    host.grid_rowconfigure(1, weight=1)
    host.grid_columnconfigure(0, weight=1)
    back = tk.Button(
        host,
        text="‹ BACK",
        command=on_back,
        bg=colors["button_background"],
        fg=colors["button_foreground"],
        activebackground=colors["button_active_background"],
        activeforeground=colors["button_active_foreground"],
        relief=tk.FLAT,
        font=("Sans", 11, "bold"),
        padx=12,
        pady=8,
    )
    back.grid(row=0, column=0, sticky="w")
    if not configured:
        setup = tk.Frame(host, bg=colors["card_background"], padx=16, pady=16)
        setup.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        tk.Label(
            setup,
            text="Set up Spotify",
            bg=colors["card_background"],
            fg=colors["title"],
            font=("Sans", 16, "bold"),
        ).pack(pady=(12, 8))
        tk.Button(
            setup,
            text="OPEN SPOTIFY SETUP",
            command=on_setup,
            bg=colors["button_active_background"],
            fg=colors["button_active_foreground"],
            relief=tk.FLAT,
            font=("Sans", 11, "bold"),
            padx=12,
            pady=8,
        ).pack()
        return host
    panel = SpotifyPlaybackPanel(host, theme=theme, show_video=False)
    panel.grid(row=1, column=0, sticky="nsew")
    retire_session = activate(panel)
    status = tk.Label(
        host,
        text=f"Looking up {artist} - {title}…",
        bg=theme["colors"]["background"],
        fg=colors["subtitle"],
        anchor="w",
        wraplength=340,
    )
    status.grid(row=2, column=0, sticky="ew", padx=8, pady=3)
    status.bind("<Configure>", lambda event: status.configure(wraplength=max(1, event.width - 8)))

    def report(message: str) -> None:
        def update() -> None:
            if host.winfo_exists():
                status.configure(text=message)

        dispatch_ui(update)

    def request_playback(local_error: str = "") -> None:
        def failed(message: str) -> None:
            def present() -> None:
                if host.winfo_exists():
                    status.configure(text="Spotify playback unavailable.")
                    cause = local_error.removeprefix("PLAYER failed: ").removeprefix(
                        "initialization_error: "
                    )
                    remedy = message.removeprefix("Spotify playback unavailable: ")
                    if remedy.startswith(("No Spotify Connect devices", "No active Spotify")):
                        remedy = "Start a song on a Spotify Connect device, then retry."
                    details = f"{cause}\n{remedy}" if cause else remedy
                    show_error("Spotify playback failed", details)

            dispatch_ui(present)

        if local_error:
            report("Trying an available Spotify Connect device…")
        request_song(artist, title, report, failed)

    if android:
        if network_allowed():
            report(f"Requesting {artist} - {title} on active Spotify device")
            request_playback()
    else:
        state = player_state()
        if not state.available:
            request_playback("Local Spotify player unavailable: " + state.message)
        else:
            deadline = monotonic() + 25.0
            request_player()

            def await_device() -> None:
                if not host.winfo_exists() or not network_allowed():
                    return
                current = player_state()
                if current.mode is SpotifyPlaybackMode.PLAYER and not current.busy:
                    report("ORC Spotify device ready. Loading selected track…")
                    request_playback()
                elif current.mode is SpotifyPlaybackMode.REMOTE and not current.busy:
                    request_playback(current.message)
                elif monotonic() >= deadline:
                    request_playback("Timed out waiting for the ORC Spotify player.")
                else:
                    host.after(200, await_device)

            host.after(200, await_device)

    def retire(event: tk.Event) -> None:
        if event.widget is host:
            retire_session()

    host.bind("<Destroy>", retire, add="+")
    return host
