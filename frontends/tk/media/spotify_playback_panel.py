from __future__ import annotations

import colorsys
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import TclError
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageTk

from frontends.tk.media.spotify_services_if import (
    ArtworkProviderIf,
    LyricsProviderIf,
    LyricsResultIf,
    MusicVideoRequestHandlerIf,
)
from ui.media import (
    MediaAvailability,
    MediaState,
    PlaybackRequestHandlerIf,
    PlaybackState,
    SeekRequestHandlerIf,
    TrackRequestHandlerIf,
    VolumeRequestHandlerIf,
)

_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS


_WATCH_VIDEO_TEXT = "Watch Video"
_RETURN_TO_SPOTIFY_TEXT = "Return to Spotify"
_FINDING_VIDEO_TEXT = "Finding video..."
_CHECKING_VIDEO_TEXT = "Checking video..."


def prepare_album_background(
    image: Image.Image,
    *,
    width: int,
    height: int,
    brightness: float = 0.24,
) -> Image.Image:
    """Create a dark, softly blurred cover image for the Spotify card."""
    if width <= 0 or height <= 0:
        raise ValueError("background dimensions must be positive")
    fitted = ImageOps.fit(
        image.convert("RGB"),
        (width, height),
        method=_LANCZOS,
    )
    blurred = fitted.filter(ImageFilter.GaussianBlur(radius=4))
    return ImageEnhance.Brightness(blurred).enhance(brightness)


def album_art_accent(image: Image.Image) -> str:
    """Return a bright, readable color sampled from album artwork."""
    sample = image.convert("RGB")
    sample.thumbnail((32, 32), _LANCZOS)
    ranked: list[tuple[float, tuple[int, int, int]]] = []
    for red, green, blue in sample.getdata():
        _hue, saturation, value = colorsys.rgb_to_hsv(
            red / 255,
            green / 255,
            blue / 255,
        )
        if value >= 0.18:
            ranked.append(
                (saturation * 0.7 + value * 0.3, (red, green, blue))
            )
    if not ranked:
        return "#FFFFFF"

    ranked.sort(reverse=True)
    colors = [color for _, color in ranked[: max(1, len(ranked) // 8)]]
    red = sum(color[0] for color in colors) // len(colors)
    green = sum(color[1] for color in colors) // len(colors)
    blue = sum(color[2] for color in colors) // len(colors)
    hue, saturation, value = colorsys.rgb_to_hsv(
        red / 255,
        green / 255,
        blue / 255,
    )
    saturation = max(0.45, min(0.85, saturation))
    value = max(0.78, min(0.98, value))
    red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)
    return (
        f"#{round(red * 255):02X}"
        f"{round(green * 255):02X}"
        f"{round(blue * 255):02X}"
    )



def format_duration_s(value: float | None) -> str:
    if value is None:
        return "--:--"

    total_seconds = max(0, int(value))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


class SpotifyPlaybackPanel(tk.Frame):
    """Render rich Spotify media state and emit semantic media requests."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        music_video_controller: MusicVideoRequestHandlerIf,
        image_cache: ArtworkProviderIf,
        lyrics_client: LyricsProviderIf,
        theme: dict[str, Any],
    ) -> None:
        self._music_video_controller = music_video_controller
        self._image_cache = image_cache
        self._lyrics_client = lyrics_client
        self._theme = theme
        self._colors = theme["colors"]
        self._layout = theme["layout"]
        self._style = theme["profiles"]["default"]

        super().__init__(parent, bg=self._colors["background"])

        self._state: MediaState | None = None
        self._playback_handler: PlaybackRequestHandlerIf | None = None
        self._track_handler: TrackRequestHandlerIf | None = None
        self._seek_handler: SeekRequestHandlerIf | None = None
        self._volume_handler: VolumeRequestHandlerIf | None = None
        self._video_operation_active = False
        self._video_available: bool | None = None
        self._video_track_key: tuple[str, str, str] | None = None
        self._video_availability_request = 0
        self._destroyed = False
        self._album_art_url: str | None = None
        self._album_art_request = 0
        self._album_art_photo: ImageTk.PhotoImage | None = None
        self._album_cover_photo: ImageTk.PhotoImage | None = None
        self._album_art_size = (0, 0)
        self._displayed_volume_percent: int | None = None
        self._pending_volume_percent: int | None = None
        self._volume_request = 0
        self._volume_worker_active = False
        self._lyrics_key: tuple[str, str, str, int] | None = None
        self._lyrics_request = 0
        self._lyrics_result: LyricsResultIf | None = None
        self._lyrics_current_var = tk.StringVar(value="")
        self._lyrics_next_var = tk.StringVar(value="")
        self._track_var = tk.StringVar(value=self._layout["loading_value"])
        self._artist_var = tk.StringVar(value=self._layout["empty_value"])
        self._album_var = tk.StringVar(value=self._layout["empty_value"])
        self._device_var = tk.StringVar(
            value=self._layout["empty_device_text"]
        )
        self._status_var = tk.StringVar(
            value=self._layout["loading_status"]
        )
        self._progress_var = tk.StringVar(
            value=self._layout["empty_progress_text"]
        )
        self._volume_var = tk.StringVar(
            value=self._layout["empty_volume_text"]
        )

        self._build_ui()

    def set_media_state(self, state: MediaState | None) -> None:
        self._state = state
        self._apply_state(state)

    def set_playback_request_handler(
        self, handler: PlaybackRequestHandlerIf | None
    ) -> None:
        self._playback_handler = handler

    def set_track_request_handler(
        self, handler: TrackRequestHandlerIf | None
    ) -> None:
        self._track_handler = handler

    def set_seek_request_handler(
        self, handler: SeekRequestHandlerIf | None
    ) -> None:
        self._seek_handler = handler

    def set_volume_request_handler(
        self, handler: VolumeRequestHandlerIf | None
    ) -> None:
        self._volume_handler = handler

    def destroy(self) -> None:
        self._destroyed = True
        super().destroy()

    def _build_ui(self) -> None:
        card = tk.Frame(
            self,
            bg=self._colors["card_background"],
            highlightthickness=self._layout["card_border_width"],
            highlightbackground=self._colors["card_border"],
        )
        card.pack(
            fill=self._layout["fill_both"],
            expand=True,
            padx=self._style["outer_pad"],
            pady=self._style["outer_pad"],
        )
        self._card = card
        self._album_art_label = tk.Label(
            card,
            bg=self._colors["card_background"],
            borderwidth=0,
        )
        self._album_art_label.place(
            x=0,
            y=0,
            relwidth=1,
            relheight=1,
        )
        card.bind(
            self._layout["configure_event"],
            self._on_card_configure,
        )

        hero = tk.Frame(card, bg=self._colors["card_background"])
        self._hero = hero
        hero.pack(
            fill=self._layout["fill_both"],
            expand=True,
            padx=self._style["hero_padx"],
            pady=self._style["hero_pady"],
        )

        cover_size = self._style["cover_size"]
        cover_frame = tk.Frame(
            hero,
            width=cover_size,
            height=cover_size,
            bg=self._colors["button_background"],
        )
        cover_frame.pack(
            side=self._layout["left_side"],
            padx=(0, self._style["cover_gap"]),
        )
        cover_frame.pack_propagate(False)
        self._album_cover_label = tk.Label(
            cover_frame,
            bg=self._colors["button_background"],
            borderwidth=0,
        )
        self._album_cover_label.pack(fill="both", expand=True)

        content = tk.Frame(
            hero,
            bg=self._colors["card_background"],
        )
        content.pack(
            side=self._layout["left_side"],
            fill=self._layout["fill_both"],
            expand=True,
        )
        content.bind(
            self._layout["configure_event"],
            self._on_content_configure,
        )

        self._track_label = self._label(
            content,
            variable=self._track_var,
            foreground=self._colors["title"],
            font=self._style["track_font"],
            anchor=self._layout["left_anchor"],
        )
        self._track_label.configure(height=1)
        self._track_label.pack(
            fill=self._layout["fill_horizontal"],
            pady=self._style["track_pady"],
        )

        metadata = tk.Frame(
            content,
            bg=self._colors["card_background"],
        )
        metadata.pack(
            fill=self._layout["fill_horizontal"],
        )

        self._label(
            metadata,
            variable=self._artist_var,
            foreground=self._colors["subtitle"],
            font=self._style["artist_font"],
            anchor=self._layout["left_anchor"],
            wraplength=self._style["text_wrap"],
        ).pack(
            fill=self._layout["fill_horizontal"],
        )

        self._label(
            metadata,
            variable=self._album_var,
            foreground=self._colors["detail"],
            font=self._style["detail_font"],
            anchor=self._layout["left_anchor"],
            wraplength=self._style["text_wrap"],
        ).pack(
            fill=self._layout["fill_horizontal"],
            pady=self._style["album_pady"],
        )

        lyrics = tk.Frame(
            content,
            bg=self._colors["card_background"],
        )
        lyrics.pack(
            fill=self._layout["fill_horizontal"],
            expand=True,
            pady=self._style["lyrics_pady"],
        )

        self._label(
            lyrics,
            variable=self._lyrics_current_var,
            foreground=self._colors["status"],
            font=self._style["lyrics_current_font"],
            anchor=self._layout["left_anchor"],
            wraplength=self._style["lyrics_wrap"],
        ).pack(fill=self._layout["fill_horizontal"])
        self._label(
            lyrics,
            variable=self._lyrics_next_var,
            foreground=self._colors["subtitle"],
            font=self._style["lyrics_font"],
            anchor=self._layout["left_anchor"],
            wraplength=self._style["lyrics_wrap"],
        ).pack(fill=self._layout["fill_horizontal"])

        self._progress_canvas = tk.Canvas(
            card,
            height=self._style["progress_canvas_height"],
            bg=self._colors["card_background"],
            highlightthickness=self._layout["zero"],
            cursor=self._layout["cursor"],
        )
        self._progress_canvas.pack(
            fill=self._layout["fill_horizontal"],
            padx=self._style["progress_padx"],
            pady=self._style["progress_canvas_pady"],
        )
        self._progress_canvas.bind(
            self._layout["click_event"],
            self._on_progress_click,
        )
        self._progress_canvas.bind(
            self._layout["drag_event"],
            self._on_progress_click,
        )
        self._progress_canvas.bind(
            self._layout["configure_event"],
            lambda _event: self._redraw_current_progress(),
        )

        self._progress_label = self._label(
            card,
            variable=self._progress_var,
            foreground=self._colors["detail"],
            font=self._style["detail_font"],
        )
        self._progress_label.pack(
            fill=self._layout["fill_horizontal"],
            padx=self._style["text_padx"],
            pady=self._style["progress_text_pady"],
        )

        controls = tk.Frame(card, bg=self._colors["card_background"])
        self._controls = controls
        controls.pack(
            side="top",
            pady=self._style["controls_pady"],
        )

        self._button(
            controls,
            self._layout["previous_text"],
            self._previous,
            width=self._style["transport_button_width"],
        ).pack(
            side=self._layout["left_side"],
            padx=self._style["transport_button_gap"],
        )

        self._play_button = self._button(
            controls,
            self._layout["play_pause_text"],
            self._play_pause,
            width=self._style["transport_button_width"],
        )
        self._play_button.pack(
            side=self._layout["left_side"],
            padx=self._style["transport_button_gap"],
        )

        self._button(
            controls,
            self._layout["next_text"],
            self._next,
            width=self._style["transport_button_width"],
        ).pack(
            side=self._layout["left_side"],
            padx=self._style["transport_button_gap"],
        )

        self._video_button = self._button(
            card,
            _WATCH_VIDEO_TEXT,
            self._toggle_video,
            width=max(
                self._style["transport_button_width"],
                len(_RETURN_TO_SPOTIFY_TEXT),
            ),
        )
        self._video_button.pack(
            side="top",
            pady=self._style["controls_pady"],
        )
        self._video_button.configure(state=tk.DISABLED)

        bottom = tk.Frame(card, bg=self._colors["card_background"])
        self._bottom = bottom
        bottom.pack(
            side="bottom",
            fill=self._layout["fill_horizontal"],
            padx=self._style["bottom_padx"],
            pady=self._style["bottom_pady"],
        )

        self._label(
            bottom,
            variable=self._device_var,
            foreground=self._colors["subtitle"],
            font=self._style["status_font"],
            anchor=self._layout["left_anchor"],
        ).pack(
            side=self._layout["left_side"],
            fill=self._layout["fill_horizontal"],
            expand=True,
        )

        volume_frame = tk.Frame(
            bottom,
            bg=self._colors["card_background"],
        )
        volume_frame.pack(side=self._layout["right_side"])

        self._button(
            volume_frame,
            self._layout["volume_down_text"],
            self._volume_down,
            width=self._style["volume_button_width"],
            vertical_padding=self._style["volume_button_pady"],
        ).pack(
            side=self._layout["left_side"],
            padx=self._style["volume_button_gap"],
        )

        self._label(
            volume_frame,
            variable=self._volume_var,
            foreground=self._colors["subtitle"],
            font=self._style["status_font"],
            width=self._style["volume_text_width"],
        ).pack(
            side=self._layout["left_side"],
            padx=self._style["volume_button_gap"],
        )

        self._button(
            volume_frame,
            self._layout["volume_up_text"],
            self._volume_up,
            width=self._style["volume_button_width"],
            vertical_padding=self._style["volume_button_pady"],
        ).pack(
            side=self._layout["left_side"],
            padx=self._style["volume_button_gap"],
        )

        self._pack_priority_sections()

    def _pack_priority_sections(self) -> None:
        """Reserve space for controls before expanding the media hero."""
        sections = (
            self._hero,
            self._progress_canvas,
            self._progress_label,
            self._controls,
            self._video_button,
            self._bottom,
        )
        for section in sections:
            section.pack_forget()

        self._bottom.pack(
            side="bottom",
            fill=self._layout["fill_horizontal"],
            padx=self._style["bottom_padx"],
            pady=self._style["bottom_pady"],
        )
        self._video_button.pack(
            side="bottom",
            pady=self._style["controls_pady"],
        )
        self._controls.pack(
            side="bottom",
            pady=self._style["controls_pady"],
        )
        self._progress_label.pack(
            side="bottom",
            fill=self._layout["fill_horizontal"],
            padx=self._style["text_padx"],
            pady=self._style["progress_text_pady"],
        )
        self._progress_canvas.pack(
            side="bottom",
            fill=self._layout["fill_horizontal"],
            padx=self._style["progress_padx"],
            pady=self._style["progress_canvas_pady"],
        )
        self._hero.pack(
            side="top",
            fill=self._layout["fill_both"],
            expand=True,
            padx=self._style["hero_padx"],
            pady=self._style["hero_pady"],
        )

    def _label(
        self,
        parent: tk.Widget,
        *,
        variable: tk.StringVar,
        foreground: str,
        font: Any,
        anchor: str | None = None,
        wraplength: int | None = None,
        width: int | None = None,
    ) -> tk.Label:
        options: dict[str, Any] = {
            "textvariable": variable,
            "bg": self._colors["card_background"],
            "fg": foreground,
            "font": font,
            "anchor": anchor or self._layout["center_anchor"],
        }

        if wraplength is not None:
            options["wraplength"] = wraplength
        if width is not None:
            options["width"] = width

        return tk.Label(parent, **options)

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        *,
        width: int,
        vertical_padding: int = 0,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            pady=vertical_padding,
            bg=self._colors["button_background"],
            fg=self._colors["button_foreground"],
            activebackground=self._colors["button_active_background"],
            activeforeground=self._colors["button_active_foreground"],
            disabledforeground=self._colors["button_disabled_foreground"],
            font=self._style["button_font"],
            bd=self._layout["zero"],
            relief=self._layout["flat_relief"],
            cursor=self._layout["cursor"],
        )

    def _on_content_configure(self, event: tk.Event) -> None:
        self._fit_track_title(max(1, event.width))

    def _fit_track_title(self, available_width: int | None = None) -> None:
        width = available_width or self._track_label.winfo_width()
        width = max(self._style["minimum_title_wrap"], width)
        family, base_size, weight = self._style["track_font"]
        title = self._track_var.get()
        selected_size = self._style["minimum_track_font_size"]
        for size in range(base_size, selected_size - 1, -1):
            candidate = tkfont.Font(family=family, size=size, weight=weight)
            if candidate.measure(title) <= width:
                selected_size = size
                break
        self._track_label.configure(
            font=(family, selected_size, weight),
            wraplength=0,
        )

    def _apply_state(self, state: MediaState | None) -> None:
        empty = self._layout["empty_value"]

        if state is None:
            self._video_track_key = None
            self._video_available = False
            self._video_availability_request += 1
            self._status_var.set(self._layout["initial_status"])
            self._track_var.set(empty)
            self._artist_var.set(empty)
            self._album_var.set(empty)
            self._device_var.set(self._layout["empty_device_text"])
            self._volume_var.set(self._layout["empty_volume_text"])
            self._progress_var.set(self._layout["empty_progress_text"])
            self._draw_progress(None)
            self._update_album_art(None)
            self._update_lyrics(None)
            self._update_video_button()
            return

        if state.availability is MediaAvailability.CONFIGURATION_REQUIRED:
            self._video_track_key = None
            self._video_available = False
            self._video_availability_request += 1
            self._status_var.set(
                self._layout["configuration_required_status"]
            )
            self._track_var.set(
                self._layout["configuration_required_title"]
            )
            self._artist_var.set(
                self._layout["configuration_required_detail"]
            )
            self._album_var.set(empty)
            self._device_var.set(self._layout["empty_device_text"])
            self._volume_var.set(self._layout["empty_volume_text"])
            self._progress_var.set(self._layout["empty_progress_text"])
            self._draw_progress(None)
            self._update_album_art(None)
            self._update_lyrics(None)
            self._update_video_button()
            return

        self._status_var.set(state.status_message)
        title = state.title or empty
        if title != self._track_var.get():
            self._track_var.set(title)
            self.after_idle(self._fit_track_title)
        self._artist_var.set(state.artist or empty)
        self._album_var.set(state.album or empty)
        self._device_var.set(
            self._layout["device_template"].format(
                device=state.device_name or empty
            )
        )

        if (
            self._pending_volume_percent is not None
            and state.volume_percent == self._pending_volume_percent
        ):
            self._pending_volume_percent = None
        displayed_volume = (
            self._pending_volume_percent
            if self._pending_volume_percent is not None
            else state.volume_percent
        )
        self._displayed_volume_percent = displayed_volume
        volume = empty if displayed_volume is None else str(displayed_volume)
        self._volume_var.set(
            self._layout["volume_template"].format(volume=volume)
        )

        self._play_button.configure(
            text=(
                self._layout["pause_text"]
                if state.playback is PlaybackState.PLAYING
                else self._layout["play_text"]
            )
        )

        self._progress_var.set(
            self._layout["progress_template"].format(
                progress=format_duration_s(state.position_s),
                duration=format_duration_s(state.duration_s),
            )
        )
        progress_percent = None
        if state.position_s is not None and state.duration_s:
            progress_percent = state.position_s / state.duration_s * 100.0
        self._draw_progress(progress_percent)
        self._update_album_art(state.artwork_uri)
        self._update_lyrics(state)
        self._update_video_availability(state)
        self._update_video_button()

    def _update_video_availability(self, state: MediaState) -> None:
        track_key = (
            state.media_uri or "",
            state.artist or "",
            state.title or "",
        )
        if not track_key[1] or not track_key[2]:
            self._video_track_key = None
            self._video_available = False
            self._video_availability_request += 1
            return
        if track_key == self._video_track_key:
            return

        self._video_track_key = track_key
        self._video_available = None
        self._video_availability_request += 1
        request = self._video_availability_request
        self._update_video_button()
        threading.Thread(
            target=self._check_video_availability_worker,
            args=(track_key, request),
            name="spotify-video-availability",
            daemon=True,
        ).start()

    def _check_video_availability_worker(
        self,
        track_key: tuple[str, str, str],
        request: int,
    ) -> None:
        try:
            available = self._music_video_controller.current_track_has_video()
        except Exception as error:
            print(f"[SpotifyPanel] Video lookup unavailable: {error}")
            available = False
        if self._destroyed:
            return
        try:
            self.after(
                0,
                lambda: self._apply_video_availability(
                    track_key, request, available
                ),
            )
        except TclError:
            pass

    def _apply_video_availability(
        self,
        track_key: tuple[str, str, str],
        request: int,
        available: bool,
    ) -> None:
        if (
            request != self._video_availability_request
            or track_key != self._video_track_key
        ):
            return
        self._video_available = available
        self._update_video_button()

    def _update_lyrics(self, state: MediaState | None) -> None:
        if (
            state is None
            or not state.title
            or not state.artist
        ):
            self._lyrics_key = None
            self._lyrics_result = None
            self._set_lyric_lines("", "")
            return

        key = (
            state.title,
            state.artist,
            state.album or "",
            int((state.duration_s or 0.0) * 1000),
        )
        if key != self._lyrics_key:
            self._lyrics_key = key
            self._lyrics_result = None
            self._lyrics_request += 1
            request = self._lyrics_request
            self._set_lyric_lines("Finding lyrics…", "")
            threading.Thread(
                target=self._load_lyrics_worker,
                args=(key, request),
                name="spotify-lyrics",
                daemon=True,
            ).start()

        self._render_lyrics(
            progress_ms=int((state.position_s or 0.0) * 1000),
            duration_ms=int((state.duration_s or 0.0) * 1000),
        )

    def _load_lyrics_worker(
        self,
        key: tuple[str, str, str, int],
        request: int,
    ) -> None:
        try:
            result = self._lyrics_client.get_lyrics(
                track_name=key[0],
                artist_name=key[1],
                album_name=key[2],
                duration_ms=key[3],
            )
        except Exception as error:
            print(f"[SpotifyPanel] Lyrics unavailable: {error}")
            result = None

        if self._destroyed:
            return
        try:
            self.after(
                0,
                lambda: self._apply_lyrics_result(
                    key=key,
                    request=request,
                    result=result,
                ),
            )
        except TclError:
            return

    def _apply_lyrics_result(
        self,
        *,
        key: tuple[str, str, str, int],
        request: int,
        result: LyricsResultIf | None,
    ) -> None:
        if request != self._lyrics_request or key != self._lyrics_key:
            return
        self._lyrics_result = result
        if result is None:
            self._set_lyric_lines("Lyrics unavailable", "")
            return
        self._render_lyrics(
            progress_ms=0,
            duration_ms=key[3],
        )

    def _render_lyrics(
        self,
        *,
        progress_ms: int,
        duration_ms: int,
    ) -> None:
        result = self._lyrics_result
        if result is None:
            return
        if result.synced_lines:
            current_index = 0
            for index, line in enumerate(result.synced_lines):
                if line.time_ms > progress_ms:
                    break
                current_index = index
            current = result.synced_lines[current_index].text
            following = (
                result.synced_lines[current_index + 1].text
                if current_index + 1 < len(result.synced_lines)
                else ""
            )
            self._set_lyric_lines(current, following)
            return

        lines = result.plain_lines
        if not lines:
            self._set_lyric_lines("Lyrics unavailable", "")
            return
        ratio = (
            min(1.0, max(0.0, progress_ms / duration_ms))
            if duration_ms > 0
            else 0.0
        )
        index = min(len(lines) - 1, int(ratio * len(lines)))
        self._set_lyric_lines(
            lines[index],
            lines[index + 1] if index + 1 < len(lines) else "",
        )

    def _set_lyric_lines(
        self,
        current: str,
        following: str,
    ) -> None:
        self._lyrics_current_var.set(current)
        self._lyrics_next_var.set(following)

    def _update_album_art(self, url: str | None) -> None:
        normalized_url = url.strip() if url else None
        if normalized_url == self._album_art_url:
            return

        self._album_art_url = normalized_url
        self._album_art_request += 1
        request = self._album_art_request
        self._track_label.configure(fg=self._colors["title"])

        if normalized_url is None:
            self._album_art_photo = None
            self._album_cover_photo = None
            self._album_art_label.configure(image="")
            self._album_cover_label.configure(image="")
            self._track_label.configure(fg=self._colors["title"])
            return

        self.update_idletasks()
        width = max(1, self._card.winfo_width())
        height = max(1, self._card.winfo_height())
        self._start_album_art_worker(
            normalized_url,
            request=request,
            width=width,
            height=height,
        )

    def _on_card_configure(self, event: tk.Event) -> None:
        if self._album_art_url is None:
            return
        width = max(1, event.width)
        height = max(1, event.height)
        previous_width, previous_height = self._album_art_size
        if (
            abs(width - previous_width) < 64
            and abs(height - previous_height) < 64
        ):
            return

        self._album_art_request += 1
        self._start_album_art_worker(
            self._album_art_url,
            request=self._album_art_request,
            width=width,
            height=height,
        )

    def _start_album_art_worker(
        self,
        url: str,
        *,
        request: int,
        width: int,
        height: int,
    ) -> None:
        self._album_art_size = (width, height)
        cache_size = max(width, height)
        threading.Thread(
            target=self._load_album_art_worker,
            args=(url, request, width, height, cache_size),
            name="spotify-album-art",
            daemon=True,
        ).start()

    def _load_album_art_worker(
        self,
        url: str,
        request: int,
        width: int,
        height: int,
        cache_size: int,
    ) -> None:
        try:
            source = self._image_cache.get(
                url,
                width=cache_size,
                height=cache_size,
            )
            try:
                background = prepare_album_background(
                    source,
                    width=width,
                    height=height,
                )
                cover_size = self._style["cover_size"]
                cover = ImageOps.fit(
                    source.convert("RGB"),
                    (cover_size, cover_size),
                    method=_LANCZOS,
                )
                accent = album_art_accent(source)
            finally:
                source.close()
        except Exception as error:
            print(f"[SpotifyPanel] Album artwork failed: {error}")
            return

        if self._destroyed:
            background.close()
            cover.close()
            return
        try:
            self.after(
                0,
                lambda: self._apply_album_art(
                    background,
                    cover,
                    accent,
                    url=url,
                    request=request,
                ),
            )
        except TclError:
            background.close()
            cover.close()

    def _apply_album_art(
        self,
        image: Image.Image,
        cover: Image.Image,
        accent: str,
        *,
        url: str,
        request: int,
    ) -> None:
        if (
            self._destroyed
            or request != self._album_art_request
            or url != self._album_art_url
        ):
            image.close()
            cover.close()
            return

        photo = ImageTk.PhotoImage(image)
        cover_photo = ImageTk.PhotoImage(cover)
        image.close()
        cover.close()
        self._album_art_photo = photo
        self._album_cover_photo = cover_photo
        self._album_art_label.configure(image=photo)
        self._album_cover_label.configure(image=cover_photo)
        self._track_label.configure(fg=accent)
        self._album_art_label.lower()

    def _on_progress_click(self, event: tk.Event) -> None:
        state = self._state
        if state is None or state.duration_s is None or state.duration_s <= 0:
            return

        width = max(
            self._layout["minimum_canvas_width"],
            self._progress_canvas.winfo_width(),
        )
        ratio = max(
            self._layout["progress_min_ratio"],
            min(
                self._layout["progress_max_ratio"],
                event.x / width,
            ),
        )
        handler = self._seek_handler
        if handler is not None:
            self._run_action(
                lambda: handler.request_seek(state.duration_s * ratio),
                failure_message="Seek failed",
            )

    def _toggle_video(self) -> None:
        if self._video_operation_active:
            return

        if self._music_video_controller.is_video_active():
            self._return_to_spotify()
            return

        if not self._video_available:
            return

        self._video_operation_active = True
        self._status_var.set(_FINDING_VIDEO_TEXT)
        self._update_video_button()

        threading.Thread(
            target=self._watch_video_worker,
            name="spotify-watch-video",
            daemon=True,
        ).start()

    def _watch_video_worker(self) -> None:
        try:
            started = self._music_video_controller.watch_current_track()
        except Exception as exc:
            self._schedule_video_result(
                started=False,
                error=exc,
            )
            return

        self._schedule_video_result(
            started=started,
            error=None,
        )

    def _schedule_video_result(
        self,
        *,
        started: bool,
        error: Exception | None,
    ) -> None:
        if self._destroyed:
            return

        try:
            self.after(
                0,
                lambda: self._finish_video_start(
                    started=started,
                    error=error,
                ),
            )
        except TclError:
            return

    def _finish_video_start(
        self,
        *,
        started: bool,
        error: Exception | None,
    ) -> None:
        self._video_operation_active = False

        if error is not None:
            self._status_var.set(f"Video failed: {error}")
            print(f"[SpotifyPanel] Video start failed: {error}")
        elif started:
            self._status_var.set("Music video playing")
        else:
            self._status_var.set("No suitable music video found")

        self._update_video_button()

    def _return_to_spotify(self) -> None:
        try:
            self._music_video_controller.return_to_spotify()
            self._status_var.set("Returned to Spotify")
        except Exception as exc:
            self._status_var.set(f"Return to Spotify failed: {exc}")
            print(f"[SpotifyPanel] Return to Spotify failed: {exc}")
        finally:
            self._update_video_button()

    def _update_video_button(self) -> None:
        if not hasattr(self, "_video_button"):
            return

        if self._video_operation_active:
            self._video_button.configure(
                text=_FINDING_VIDEO_TEXT,
                state=tk.DISABLED,
            )
            return

        if self._music_video_controller.is_video_active():
            self._video_button.configure(
                text=_RETURN_TO_SPOTIFY_TEXT,
                state=tk.NORMAL,
            )
            return
        if self._video_available is None:
            self._video_button.configure(
                text=_CHECKING_VIDEO_TEXT,
                state=tk.DISABLED,
            )
            return
        self._video_button.configure(
            text=_WATCH_VIDEO_TEXT,
            state=(tk.NORMAL if self._video_available else tk.DISABLED),
        )

    def _play_pause(self) -> None:
        handler = self._playback_handler
        if handler is None:
            return
        request = (
            handler.request_pause
            if self._state is not None
            and self._state.playback is PlaybackState.PLAYING
            else handler.request_play
        )
        self._run_action(
            request,
            failure_message="Play/pause failed",
        )

    def _next(self) -> None:
        if self._track_handler is None:
            return
        self._run_action(
            self._track_handler.request_next_track,
            failure_message="Next track failed",
        )

    def _previous(self) -> None:
        if self._track_handler is None:
            return
        self._run_action(
            self._track_handler.request_previous_track,
            failure_message="Previous track failed",
        )

    def _volume_up(self) -> None:
        self._adjust_volume(self._layout["volume_step"])

    def _volume_down(self) -> None:
        self._adjust_volume(-self._layout["volume_step"])

    def _adjust_volume(self, delta: int) -> None:
        current = (
            self._pending_volume_percent
            if self._pending_volume_percent is not None
            else self._displayed_volume_percent
        )
        if current is None:
            current = self._layout["default_volume"]
        target = max(
            self._layout["minimum_volume"],
            min(
                self._layout["maximum_volume"],
                current + delta,
            ),
        )
        self._pending_volume_percent = target
        self._displayed_volume_percent = target
        self._volume_var.set(
            self._layout["volume_template"].format(volume=target)
        )
        self._volume_request += 1
        if self._volume_worker_active:
            return
        self._volume_worker_active = True
        self.after(0, self._set_volume_worker)

    def _set_volume_worker(self) -> None:
        while not self._destroyed:
            target = self._pending_volume_percent
            request = self._volume_request
            if target is None:
                self._volume_worker_active = False
                return

            try:
                if self._volume_handler is None:
                    raise RuntimeError("Spotify volume control is unavailable")
                self._volume_handler.request_volume(target)
            except Exception as error:
                self._volume_worker_active = False
                try:
                    self.after(
                        0,
                        lambda error=error, request=request: (
                            self._finish_volume_adjustment(
                                request=request,
                                error=error,
                            )
                        ),
                    )
                except TclError:
                    pass
                return
            if request == self._volume_request:
                self._volume_worker_active = False
                try:
                    self.after(
                        1500,
                        lambda: self._finish_volume_confirmation(
                            request
                        ),
                    )
                except TclError:
                    pass
                return

        self._volume_worker_active = False

    def _finish_volume_confirmation(self, request: int) -> None:
        if request == self._volume_request:
            self._pending_volume_percent = None

    def _finish_volume_adjustment(
        self,
        *,
        request: int,
        error: Exception,
    ) -> None:
        if request != self._volume_request:
            return
        self._pending_volume_percent = None
        self._status_var.set(
            self._layout["volume_not_supported_text"]
        )
        print(f"[SpotifyPanel] Volume adjustment failed: {error}")

    def _run_action(
        self,
        action,
        *,
        failure_message: str,
    ) -> None:
        try:
            action()
        except Exception as exc:
            self._status_var.set(failure_message)
            print(f"[SpotifyPanel] {failure_message}: {exc}")

    def _redraw_current_progress(self) -> None:
        state = self._state
        progress_percent = None
        if state is not None and state.position_s is not None and state.duration_s:
            progress_percent = state.position_s / state.duration_s * 100.0
        self._draw_progress(progress_percent)

    def _draw_progress(self, progress_percent: float | None) -> None:
        self._progress_canvas.delete(self._layout["canvas_all_tag"])

        width = max(
            self._layout["fallback_canvas_width"],
            self._progress_canvas.winfo_width(),
        )

        self._progress_canvas.create_rectangle(
            self._layout["progress_left"],
            self._style["progress_track_top"],
            width,
            self._style["progress_track_bottom"],
            fill=self._colors["progress_track"],
            outline=self._layout["empty_outline"],
        )

        if progress_percent is None:
            return

        fill_width = (
            width
            * max(
                self._layout["minimum_progress_percent"],
                min(
                    self._layout["maximum_progress_percent"],
                    progress_percent,
                ),
            )
            / self._layout["maximum_progress_percent"]
        )

        self._progress_canvas.create_rectangle(
            self._layout["progress_left"],
            self._style["progress_track_top"],
            fill_width,
            self._style["progress_track_bottom"],
            fill=self._colors["progress_fill"],
            outline=self._layout["empty_outline"],
        )
