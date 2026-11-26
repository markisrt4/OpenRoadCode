"""Render a cached artist biography and credited Wikimedia portrait."""

import tkinter as tk
from io import BytesIO

from PIL import Image, ImageOps, ImageTk

from ui.media.artist_profile import ArtistProfile
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget


class TrendingArtistDetails(tk.Frame, UiWidget):
    """Display artist context using only the injected profile snapshot."""

    def __init__(self, parent: tk.Misc, theme: ThemeBundle) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.surface, padx=16, pady=14)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._header = tk.Frame(self, bg=ui.surface_alt, padx=14, pady=11)
        self._header.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self._header.columnconfigure(0, weight=1)
        self._accent = tk.Canvas(self, height=5, highlightthickness=0, bg=ui.surface_alt)
        self._accent.grid(row=0, column=0, sticky="ew")
        self._accent_colors = (self.winfo_rgb(ui.accent_primary), self.winfo_rgb(ui.surface_alt))
        self._accent.bind("<Configure>", self._paint_accent)
        self._title = tk.Label(
            self._header,
            bg=ui.surface_alt,
            fg=ui.text,
            anchor="w",
            justify=tk.LEFT,
            font=("DejaVu Sans", 25, "bold"),
        )
        self._subtitle = tk.Label(
            self._header,
            bg=ui.surface_alt,
            fg=ui.text,
            anchor="w",
            justify=tk.LEFT,
            font=("DejaVu Sans", 15),
        )
        self._title.grid(row=0, column=0, sticky="ew")
        self._subtitle.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self._body = tk.Frame(self, bg=ui.surface)
        self._body.grid(row=2, column=0, sticky="nsew")
        self._body.columnconfigure(1, weight=1)
        self._body.rowconfigure(0, weight=1)
        self._portrait = tk.Label(self._body, bg=ui.surface_alt, bd=0)
        self._portrait.grid(row=0, column=0, sticky="n", padx=(0, 14))
        self._portrait.grid_remove()
        self._bio = tk.Text(
            self._body,
            width=1,
            height=1,
            bg=ui.surface,
            fg=ui.text,
            font=("DejaVu Sans", 16),
            spacing1=2,
            spacing3=6,
            wrap=tk.WORD,
            relief=tk.FLAT,
            highlightthickness=0,
            state=tk.DISABLED,
        )
        self._bio.grid(row=0, column=1, sticky="nsew")
        self._scrollbar = tk.Scrollbar(
            self._body, orient=tk.VERTICAL, width=22, command=self._bio.yview
        )
        self._scrollbar.grid(row=0, column=2, sticky="ns")
        self._bio.configure(yscrollcommand=self._scrollbar.set)
        self._body.grid_remove()
        self._credit = tk.Label(
            self, bg=ui.surface, fg=ui.text_muted, anchor="w", justify=tk.LEFT, font=("DejaVu Sans", 10)
        )
        self._credit.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        self._credit.grid_remove()
        self._photo: ImageTk.PhotoImage | None = None
        self._artist: str | None = None
        self.bind("<Configure>", self._resize)

    def _paint_accent(self, event: tk.Event) -> None:
        self._accent.delete("all")
        start, end = self._accent_colors
        steps = 48
        for step in range(steps):
            channels = [
                (first + (last - first) * step // (steps - 1)) >> 8
                for first, last in zip(start, end, strict=True)
            ]
            color = "#{:02x}{:02x}{:02x}".format(*channels)
            self._accent.create_rectangle(
                step * event.width // steps,
                0,
                (step + 1) * event.width // steps,
                event.height,
                fill=color,
                width=0,
            )

    def _resize(self, event: tk.Event) -> None:
        for label in (self._title, self._subtitle):
            label.configure(wraplength=max(1, event.width - 60))
        self._credit.configure(wraplength=max(1, event.width - 32))

    def set_selection(self, title: str, subtitle: str, *, artist: str | None = None) -> None:
        if self._artist != artist:
            self._artist = artist
            self.set_profile(None)
        self._title.configure(text=title)
        self._subtitle.configure(text=subtitle)

    def set_profile(self, profile: ArtistProfile | None) -> None:
        """Clear previous content and render a new artist snapshot."""
        self._portrait.grid_remove()
        self._portrait.configure(image="")
        self._photo = None
        self._bio.configure(state=tk.NORMAL)
        self._bio.delete("1.0", tk.END)
        if profile is not None:
            self._bio.insert("1.0", profile.biography, ())
        self._bio.configure(state=tk.DISABLED)
        self._bio.yview_moveto(0)
        if profile is None:
            self._body.grid_remove()
            self._credit.grid_remove()
            return
        self._body.grid()
        self._credit.configure(
            text=f"About {profile.name} · Wikipedia (CC BY-SA) · Artist photo unavailable"
        )
        self._credit.grid()
        if not profile.portrait:
            return
        try:
            with Image.open(BytesIO(profile.portrait)) as image:
                portrait = ImageOps.exif_transpose(image)
                portrait.thumbnail((168, 178), Image.Resampling.LANCZOS)
                self._photo = ImageTk.PhotoImage(portrait, master=self)
        except (OSError, ValueError):
            return
        self._portrait.configure(image=self._photo)
        self._portrait.grid()
        self._credit.configure(
            text=f"About {profile.name} · Wikipedia (CC BY-SA)\nPhoto: {profile.portrait_credit}"
        )
