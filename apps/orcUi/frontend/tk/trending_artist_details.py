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
        self._header = tk.Canvas(self, highlightthickness=0, bg=ui.surface_alt)
        self._header.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self._header_colors = (self.winfo_rgb(ui.surface_alt), self.winfo_rgb(ui.surface))
        self._title = self._header.create_text(
            14, 10, anchor="nw", fill=ui.text, font=("DejaVu Sans", 25, "bold")
        )
        self._subtitle = self._header.create_text(
            14, 10, anchor="nw", fill=ui.text, font=("DejaVu Sans", 15)
        )
        self._header.bind("<Configure>", self._layout_header)

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
        controls = tk.Frame(self._body, bg=ui.surface)
        controls.grid(row=0, column=2, sticky="ns", padx=(8, 0))
        for text, direction in (("▲", -1), ("▼", 1)):
            tk.Button(
                controls,
                text=text,
                command=lambda step=direction: self._bio.yview_scroll(step, "pages"),
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground=ui.text,
                relief=tk.FLAT,
                font=("DejaVu Sans", 18, "bold"),
                padx=12,
                pady=8,
            ).pack(fill=tk.X, pady=(0, 6))
        self._scroll_controls = controls
        self._body.grid_remove()
        self._credit = tk.Label(
            self, bg=ui.surface, fg=ui.text_muted, anchor="w", justify=tk.LEFT, font=("DejaVu Sans", 10)
        )
        self._credit.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        self._credit.grid_remove()
        self._photo: ImageTk.PhotoImage | None = None
        self._artist: str | None = None
        self.bind("<Configure>", self._resize)

    def _layout_header(self, _event: tk.Event | None = None) -> None:
        width = self._header.winfo_width()
        if width <= 1:
            return
        for item in (self._title, self._subtitle):
            self._header.itemconfigure(item, width=max(1, width - 28))
        title_bounds = self._header.bbox(self._title)
        self._header.coords(self._subtitle, 14, (title_bounds[3] if title_bounds else 10) + 4)
        bounds = self._header.bbox(self._subtitle)
        height = max(66, (bounds[3] if bounds else 0) + 10)
        self._header.configure(height=height)
        self._header.delete("gradient")
        start, end = self._header_colors
        steps = 48
        for step in range(steps):
            channels = [
                (first + (last - first) * step // (steps - 1)) >> 8
                for first, last in zip(start, end, strict=True)
            ]
            self._header.create_rectangle(
                step * width // steps,
                0,
                (step + 1) * width // steps,
                height,
                fill="#{:02x}{:02x}{:02x}".format(*channels),
                width=0,
                tags=("gradient",),
            )
        self._header.tag_lower("gradient")

    def _resize(self, event: tk.Event) -> None:
        self._credit.configure(wraplength=max(1, event.width - 32))

    def set_selection(self, title: str, subtitle: str, *, artist: str | None = None) -> None:
        if self._artist != artist:
            self._artist = artist
            self.set_profile(None)
        self._header.itemconfigure(self._title, text=title)
        self._header.itemconfigure(self._subtitle, text=subtitle)
        self._layout_header()

    def show_loading(self) -> None:
        self.set_profile(None)
        self._set_biography("Loading artist information…")

    def _set_biography(self, text: str) -> None:
        self._bio.configure(state=tk.NORMAL)
        self._bio.delete("1.0", tk.END)
        self._bio.insert("1.0", text)
        self._bio.configure(state=tk.DISABLED)
        self._bio.yview_moveto(0)
        self._body.grid()

    def set_profile(self, profile: ArtistProfile | None) -> None:
        """Clear previous content and render a new artist snapshot."""
        self._portrait.grid_remove()
        self._portrait.configure(image="")
        self._photo = None
        self._credit.grid_remove()
        self._scroll_controls.grid_remove()
        if profile is None:
            if self._artist is None:
                self._body.grid_remove()
            else:
                self._set_biography("Artist information unavailable.")
            return
        self._set_biography(profile.biography)
        self._scroll_controls.grid()
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
