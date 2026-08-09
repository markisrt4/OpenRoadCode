from __future__ import annotations

import tkinter as tk
from typing import Any

from ui.media import (
    MediaAvailability,
    MediaState,
    PlaybackRequestHandlerIf,
    PlaybackState,
    SeekRequestHandlerIf,
    TrackRequestHandlerIf,
    VolumeRequestHandlerIf,
)
def format_duration_s(value: float | None) -> str:
    if value is None:
        return "--:--"

    total_seconds = max(0, int(value))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


class SpotifyPlaybackPanel(tk.Frame):
    """Render generic media state and emit playback requests."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        theme: dict[str, Any],
    ) -> None:
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
        self._track_var = tk.StringVar(value=self._layout["empty_value"])
        self._artist_var = tk.StringVar(value=self._layout["empty_value"])
        self._album_var = tk.StringVar(value=self._layout["empty_value"])
        self._device_var = tk.StringVar(
            value=self._layout["empty_device_text"]
        )
        self._status_var = tk.StringVar(
            value=self._layout["initial_status"]
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
        self,
        handler: PlaybackRequestHandlerIf | None,
    ) -> None:
        self._playback_handler = handler

    def set_track_request_handler(
        self,
        handler: TrackRequestHandlerIf | None,
    ) -> None:
        self._track_handler = handler

    def set_seek_request_handler(
        self,
        handler: SeekRequestHandlerIf | None,
    ) -> None:
        self._seek_handler = handler

    def set_volume_request_handler(
        self,
        handler: VolumeRequestHandlerIf | None,
    ) -> None:
        self._volume_handler = handler

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=self._colors["background"])
        header.pack(
            fill=self._layout["fill_horizontal"],
            padx=self._style["outer_pad"],
            pady=self._style["header_pady"],
        )

        tk.Label(
            header,
            text=self._layout["title"],
            bg=self._colors["background"],
            fg=self._colors["title"],
            font=self._style["header_title_font"],
            anchor=self._layout["left_anchor"],
        ).pack(side=self._layout["left_side"])

        tk.Label(
            header,
            textvariable=self._status_var,
            bg=self._colors["background"],
            fg=self._colors["status"],
            font=self._style["status_font"],
            anchor=self._layout["right_anchor"],
        ).pack(side=self._layout["right_side"])

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

        self._label(
            card,
            variable=self._track_var,
            foreground=self._colors["title"],
            font=self._style["track_font"],
            wraplength=self._style["text_wrap"],
        ).pack(
            fill=self._layout["fill_horizontal"],
            padx=self._style["text_padx"],
            pady=self._style["track_pady"],
        )

        self._label(
            card,
            variable=self._artist_var,
            foreground=self._colors["subtitle"],
            font=self._style["artist_font"],
            wraplength=self._style["text_wrap"],
        ).pack(
            fill=self._layout["fill_horizontal"],
            padx=self._style["text_padx"],
        )

        self._label(
            card,
            variable=self._album_var,
            foreground=self._colors["detail"],
            font=self._style["detail_font"],
            wraplength=self._style["text_wrap"],
        ).pack(
            fill=self._layout["fill_horizontal"],
            padx=self._style["text_padx"],
            pady=self._style["album_pady"],
        )

        self._progress_canvas = tk.Canvas(
            card,
            height=self._style["progress_canvas_height"],
            bg=self._colors["card_background"],
            highlightthickness=self._layout["zero"],
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

        self._label(
            card,
            variable=self._progress_var,
            foreground=self._colors["detail"],
            font=self._style["detail_font"],
        ).pack(
            fill=self._layout["fill_horizontal"],
            padx=self._style["text_padx"],
            pady=self._style["progress_text_pady"],
        )

        controls = tk.Frame(card, bg=self._colors["card_background"])
        controls.pack(pady=self._style["controls_pady"])

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

        bottom = tk.Frame(card, bg=self._colors["card_background"])
        bottom.pack(
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
        ).pack(
            side=self._layout["left_side"],
            padx=self._style["volume_button_gap"],
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
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=self._colors["button_background"],
            fg=self._colors["button_foreground"],
            activebackground=self._colors["button_active_background"],
            activeforeground=self._colors["button_active_foreground"],
            font=self._style["button_font"],
            bd=self._layout["zero"],
            relief=self._layout["flat_relief"],
            cursor=self._layout["cursor"],
        )

    def _apply_state(self, state: MediaState | None) -> None:
        empty = self._layout["empty_value"]

        if (
            state is not None
            and state.availability is MediaAvailability.CONFIGURATION_REQUIRED
        ):
            self._status_var.set(
                state.status_message
                or self._layout["configuration_required_status"]
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
            return

        if state is None:
            state = MediaState()

        self._status_var.set(
            state.status_message or self._layout["initial_status"]
        )
        self._track_var.set(state.title or empty)
        self._artist_var.set(state.artist or empty)
        self._album_var.set(state.album or empty)
        self._device_var.set(
            self._layout["device_template"].format(
                device=state.device_name or empty
            )
        )

        volume = (
            empty
            if state.volume_percent is None
            else str(state.volume_percent)
        )
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
        self._draw_progress(self._progress_percent(state))

    def _on_progress_click(self, event: tk.Event) -> None:
        state = self._state
        handler = self._seek_handler
        if (
            state is None
            or state.duration_s is None
            or state.duration_s <= 0
            or handler is None
        ):
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
        position_s = state.duration_s * ratio

        self._run_action(
            lambda: handler.request_seek(position_s),
            failure_message="Seek failed",
        )

    def _play_pause(self) -> None:
        handler = self._playback_handler
        if handler is None:
            return

        is_playing = (
            self._state is not None
            and self._state.playback is PlaybackState.PLAYING
        )
        self._run_action(
            handler.request_pause if is_playing else handler.request_play,
            failure_message="Play/pause failed",
        )

    def _next(self) -> None:
        handler = self._track_handler
        if handler is None:
            return
        self._run_action(
            handler.request_next_track,
            failure_message="Next track failed",
        )

    def _previous(self) -> None:
        handler = self._track_handler
        if handler is None:
            return
        self._run_action(
            handler.request_previous_track,
            failure_message="Previous track failed",
        )

    def _volume_up(self) -> None:
        self._adjust_volume(self._layout["volume_step"])

    def _volume_down(self) -> None:
        self._adjust_volume(-self._layout["volume_step"])

    def _adjust_volume(self, delta: int) -> None:
        handler = self._volume_handler
        if handler is None:
            return

        try:
            state = self._state
            current = (
                state.volume_percent
                if state is not None and state.volume_percent is not None
                else self._layout["default_volume"]
            )
            target = max(
                self._layout["minimum_volume"],
                min(
                    self._layout["maximum_volume"],
                    current + delta,
                ),
            )
            handler.request_volume(target)
        except Exception as exc:
            self._status_var.set(
                self._layout["volume_not_supported_text"]
            )
            print(f"[SpotifyPlaybackPanel] Volume adjustment failed: {exc}")

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
            print(f"[SpotifyPlaybackPanel] {failure_message}: {exc}")

    def _redraw_current_progress(self) -> None:
        self._draw_progress(self._progress_percent(self._state))

    @staticmethod
    def _progress_percent(state: MediaState | None) -> float | None:
        if (
            state is None
            or state.position_s is None
            or state.duration_s is None
            or state.duration_s <= 0
        ):
            return None
        return max(0.0, min(100.0, state.position_s * 100.0 / state.duration_s))

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
