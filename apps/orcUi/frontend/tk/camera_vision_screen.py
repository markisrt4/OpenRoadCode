# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk presentation for the contract-bound camera and perception screen."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode
from ui.vision.vision_request_handler_if import VisionRequestHandlerIf
from ui.vision.vision_ui_if import VisionUiIf
from ui.vision.vision_ui_state import (
    VisionCameraMode,
    VisionLifecycle,
    VisionObject,
    VisionPixelFormat,
    VisionUiState,
)


class CameraVisionScreen(TkScreen, VisionUiIf):
    """Render immutable vision state and emit semantic user requests."""

    def __init__(self, host: TkScreenHostIf, *, theme_bundle: Callable[[], ThemeBundle]) -> None:
        super().__init__(ScreenId("camera-vision"))
        self._host = host
        self._theme_bundle = theme_bundle
        self._request_handler: VisionRequestHandlerIf | None = None
        self._state = VisionUiState()
        self._panel: tk.Frame | None = None
        self._canvas: tk.Canvas | None = None
        self._status_label: tk.Label | None = None
        self._mode_label: tk.Label | None = None
        self._ai_button: tk.Button | None = None
        self._photo: object | None = None

    def set_vision_request_handler(self, handler: VisionRequestHandlerIf | None) -> None:
        """Connect semantic controls to their request receiver.

        @param handler Request receiver, or None to disconnect controls.
        """
        self._request_handler = handler

    def set_vision_state(self, state: VisionUiState) -> None:
        """Render one complete immutable vision snapshot.

        @param state Latest vision presentation state.
        """
        self._state = state
        if self._panel is not None and self._panel.winfo_exists():
            self._render_state()

    def show(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("VISION")
        self._build_panel()
        self._render_state()
        if self._request_handler is not None:
            self._request_handler.request_activate()

    def hide(self) -> None:
        if self._request_handler is not None:
            self._request_handler.request_deactivate()
        self._panel = None
        self._canvas = None
        self._status_label = None
        self._mode_label = None
        self._ai_button = None
        self._photo = None

    def set_theme_mode(self, mode: ThemeMode) -> None:
        """Rebuild the active screen after a theme change.

        @param mode Newly selected application theme mode.
        """
        del mode
        if self._panel is not None and self._panel.winfo_exists():
            self.show()

    def _build_panel(self) -> None:
        theme = self._theme_bundle().ui
        panel = tk.Frame(self._host.screen_parent, bg=theme.background)
        panel.pack(fill=tk.BOTH, expand=True)
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)
        self._canvas = tk.Canvas(
            panel, bg="#000000", highlightthickness=1, highlightbackground=theme.border
        )
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        controls = tk.Frame(panel, bg=theme.surface, width=180)
        controls.grid(row=0, column=1, sticky="ns")
        controls.grid_propagate(False)
        tk.Label(
            controls, text="CAMERA / VISION", bg=theme.surface, fg=theme.text,
            font=("Sans", 12, "bold"),
        ).pack(fill=tk.X, padx=8, pady=(10, 8))
        self._mode_label = tk.Label(
            controls, text="", bg=theme.surface, fg=theme.text_muted,
            font=("Sans", 9, "bold"),
        )
        self._mode_label.pack(fill=tk.X, padx=8, pady=(0, 6))

        for mode in (VisionCameraMode.AUTO, VisionCameraMode.DAY, VisionCameraMode.LOW_LIGHT):
            tk.Button(
                controls,
                text=mode.value.upper().replace("_", " "),
                command=lambda selected=mode: self._request_mode(selected),
                bg=theme.control_background,
                fg=theme.control_text,
                activebackground=theme.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                highlightthickness=0,
                pady=7,
            ).pack(fill=tk.X, padx=8, pady=2)

        self._ai_button = tk.Button(
            controls,
            command=self._request_ai_change,
            bg=theme.control_background,
            fg=theme.control_text,
            activebackground=theme.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            pady=7,
        )
        self._ai_button.pack(fill=tk.X, padx=8, pady=(12, 2))
        self._status_label = tk.Label(
            controls, text="", justify=tk.LEFT, anchor="nw",
            bg=theme.surface, fg=theme.text_muted, font=("Monospace", 9),
        )
        self._status_label.pack(fill=tk.X, padx=8, pady=(12, 4))
        self._panel = panel

    def _request_mode(self, mode: VisionCameraMode) -> None:
        handler = self._request_handler
        if handler is not None:
            handler.request_camera_mode(mode)

    def _request_ai_change(self) -> None:
        handler = self._request_handler
        if handler is not None:
            handler.request_ai_enabled(not self._state.ai_enabled)

    def _render_state(self) -> None:
        state = self._state
        requested = state.requested_mode.value.upper().replace("_", " ")
        effective = state.effective_mode.value.upper().replace("_", " ")
        if self._mode_label is not None:
            text = requested if state.requested_mode is not VisionCameraMode.AUTO else f"AUTO → {effective}"
            self._mode_label.configure(text=f"Mode: {text}")
        if self._ai_button is not None:
            self._ai_button.configure(
                text="Disable AI" if state.ai_enabled else "Enable AI",
                state=tk.NORMAL if state.lifecycle is not VisionLifecycle.STARTING else tk.DISABLED,
            )
        if self._status_label is not None:
            oldest = max((item.track_age_s or 0.0 for item in state.objects), default=0.0)
            metrics = (
                f"CAM {state.camera_rate_hz:4.1f} Hz\n"
                f"AI  {'ON ' if state.ai_enabled else 'OFF'} {state.inference_rate_hz:4.1f} Hz\n"
                f"INF {state.inference_latency_s * 1000.0:4.0f} ms\n"
                f"OBJ {len(state.objects)}\n"
                f"AGE {oldest:4.1f} s\n"
                f"LUM {state.luminance_ratio:4.0%}\n"
                f"SRC {state.source_label}"
            )
            self._status_label.configure(
                text=f"{state.status_message}\n{metrics}" if state.status_message else metrics
            )
        self._draw_image()

    def _draw_image(self) -> None:
        canvas = self._canvas
        image = self._state.image
        if canvas is None or image is None:
            if canvas is not None:
                canvas.delete("all")
                canvas.update_idletasks()
                theme = self._theme_bundle().ui
                canvas.create_text(
                    max(1, canvas.winfo_width()) // 2,
                    max(1, canvas.winfo_height()) // 2,
                    text=self._empty_image_message(self._state),
                    anchor=tk.CENTER,
                    justify=tk.CENTER,
                    fill=theme.text_muted,
                    font=("Sans", 16, "bold"),
                    width=max(200, canvas.winfo_width() - 80),
                )
            return
        if image.pixel_format is not VisionPixelFormat.RGB888:
            raise ValueError(f"Unsupported vision pixel format: {image.pixel_format}")
        try:
            from PIL import Image, ImageTk
        except ModuleNotFoundError as exc:
            raise RuntimeError("Pillow is required for the VISION screen") from exc

        canvas.update_idletasks()
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        scale = min(width / image.width, height / image.height)
        draw_width = max(1, int(image.width * scale))
        draw_height = max(1, int(image.height * scale))
        offset_x = (width - draw_width) // 2
        offset_y = (height - draw_height) // 2
        source = Image.frombytes(
            "RGB", (image.width, image.height), image.data,
            "raw", "RGB", image.stride_bytes,
        )
        resized = source.resize((draw_width, draw_height), Image.Resampling.BILINEAR)
        photo = ImageTk.PhotoImage(resized)
        self._photo = photo
        canvas.delete("all")
        canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=photo)
        self._draw_objects(
            canvas, self._state.objects, offset_x, offset_y, draw_width, draw_height
        )

    @staticmethod
    def _empty_image_message(state: VisionUiState) -> str:
        if state.status_message:
            return state.status_message
        if state.lifecycle is VisionLifecycle.STARTING:
            return "Starting camera…"
        if state.lifecycle is VisionLifecycle.RUNNING:
            return "Waiting for camera frames…"
        if state.lifecycle is VisionLifecycle.ERROR:
            return "Camera unavailable"
        return "Camera is not active"

    @staticmethod
    def _draw_objects(
        canvas: tk.Canvas,
        objects: tuple[VisionObject, ...],
        offset_x: int,
        offset_y: int,
        width: int,
        height: int,
    ) -> None:
        for item in objects:
            x1 = offset_x + int(item.x * width)
            y1 = offset_y + int(item.y * height)
            x2 = x1 + int(item.width * width)
            y2 = y1 + int(item.height * height)
            canvas.create_rectangle(x1, y1, x2, y2, outline="#00ff77", width=2)
            identity = "" if item.track_id is None else f" #{item.track_id}"
            label = f"{item.label.upper()}{identity} {item.confidence:.0%}"
            canvas.create_text(
                x1 + 4, max(offset_y + 8, y1 - 4), text=label,
                anchor=tk.SW, fill="#00ff77", font=("Sans", 9, "bold"),
            )
