# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Isolated orcUi camera/perception evaluation screen."""

from __future__ import annotations

import time
import tkinter as tk
from collections.abc import Callable

from controllers.computer_vision.camera_frame_processor import CameraFrameProcessor, CameraMode
from controllers.computer_vision.object_detector_if import DetectionFrame
from controllers.computer_vision.perception_worker import PerceptionWorker
from controllers.computer_vision.yolo_object_detector import YoloObjectDetector
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from hardware_io.camera.v4l2_camera import V4L2Camera
from hardware_io.camera.v4l2_camera_controls import (
    V4L2CameraProfile,
    V4L2CameraProfileController,
)
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle, ThemeMode


class CameraVisionScreen(TkScreen):
    """Live camera preview and perception playground for orcUi."""

    _POLL_MS = 15

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        device: str = "/dev/video0",
        model_name: str = "yolo11n.pt",
    ) -> None:
        super().__init__(ScreenId("camera-vision"))
        self._host = host
        self._theme_bundle = theme_bundle
        self._device = device
        self._model_name = model_name
        self._panel: tk.Frame | None = None
        self._canvas: tk.Canvas | None = None
        self._status_label: tk.Label | None = None
        self._mode_label: tk.Label | None = None
        self._photo: object | None = None
        self._poll_id: object | None = None
        self._camera: V4L2Camera | None = None
        self._worker: PerceptionWorker | None = None
        self._processor = CameraFrameProcessor()
        self._hardware_controls = V4L2CameraProfileController(device)
        self._ai_enabled = True
        self._last_detection: DetectionFrame | None = None
        self._last_capture_time = 0.0
        self._camera_fps = 0.0
        self._last_ai_count = 0
        self._last_ai_time = 0.0
        self._ai_fps = 0.0

    def show(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("VISION")
        self._build_panel()
        self._start_runtime()
        self._schedule_poll()

    def hide(self) -> None:
        self._cancel_poll()
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.stop()
        camera = self._camera
        self._camera = None
        if camera is not None:
            try:
                self._hardware_controls.restore_day_defaults()
            except RuntimeError:
                pass
            camera.close()
        self._panel = None
        self._canvas = None
        self._status_label = None
        self._mode_label = None
        self._photo = None
        self._last_detection = None

    def set_theme_mode(self, mode: ThemeMode) -> None:
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
            panel,
            bg="#000000",
            highlightthickness=1,
            highlightbackground=theme.border,
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

        for mode in (CameraMode.AUTO, CameraMode.DAY, CameraMode.LOW_LIGHT):
            tk.Button(
                controls,
                text=mode.value.upper().replace("_", " "),
                command=lambda selected=mode: self._set_mode(selected),
                bg=theme.control_background,
                fg=theme.control_text,
                activebackground=theme.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                pady=7,
            ).pack(fill=tk.X, padx=8, pady=2)

        tk.Button(
            controls,
            text="AI ON / OFF",
            command=self._toggle_ai,
            bg=theme.control_background,
            fg=theme.control_text,
            activebackground=theme.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            pady=7,
        ).pack(fill=tk.X, padx=8, pady=(12, 2))

        self._status_label = tk.Label(
            controls,
            text="Starting camera...",
            justify=tk.LEFT,
            anchor="nw",
            bg=theme.surface,
            fg=theme.text_muted,
            font=("Monospace", 9),
        )
        self._status_label.pack(fill=tk.X, padx=8, pady=(12, 4))
        self._panel = panel
        self._update_mode_label()

    def _start_runtime(self) -> None:
        camera = V4L2Camera(self._device, width=1920, height=1080, fps=30.0, pixel_format="MJPG")
        camera.open()
        self._hardware_controls.restore_day_defaults()
        detector = YoloObjectDetector(self._model_name, confidence=0.35, image_size=640)
        worker = PerceptionWorker(detector)
        worker.start()
        self._camera = camera
        self._worker = worker
        self._last_capture_time = time.perf_counter()
        self._last_ai_time = self._last_capture_time
        self._last_ai_count = 0

    def _schedule_poll(self) -> None:
        self._poll_id = self._host.schedule_ui_callback(self._POLL_MS, self._poll)

    def _cancel_poll(self) -> None:
        poll_id = self._poll_id
        self._poll_id = None
        if poll_id is not None:
            try:
                self._host.cancel_ui_callback(poll_id)
            except (RuntimeError, tk.TclError):
                pass

    def _poll(self) -> None:
        self._poll_id = None
        camera = self._camera
        worker = self._worker
        canvas = self._canvas
        if camera is None or worker is None or canvas is None:
            return

        try:
            frame = camera.read()
            now = time.perf_counter()
            elapsed = now - self._last_capture_time
            if elapsed > 0:
                instantaneous = 1.0 / elapsed
                self._camera_fps = instantaneous if self._camera_fps == 0.0 else (0.9 * self._camera_fps + 0.1 * instantaneous)
            self._last_capture_time = now

            processed_image = self._processor.process(frame.image)
            self._sync_hardware_profile()
            if self._ai_enabled:
                from hardware_io.camera.camera_if import CameraFrame
                worker.submit(CameraFrame(processed_image, frame.timestamp_s, frame.sequence))

            detection = worker.latest_result
            if detection is not None:
                self._last_detection = detection

            processed_count = worker.processed_frames
            if processed_count != self._last_ai_count:
                ai_elapsed = now - self._last_ai_time
                delta = processed_count - self._last_ai_count
                if ai_elapsed > 0 and delta > 0:
                    measured = delta / ai_elapsed
                    self._ai_fps = measured if self._ai_fps == 0.0 else (0.8 * self._ai_fps + 0.2 * measured)
                self._last_ai_count = processed_count
                self._last_ai_time = now

            self._draw(processed_image, self._last_detection if self._ai_enabled else None)
            self._update_status()
        except Exception as exc:
            if self._status_label is not None:
                self._status_label.configure(text=f"Camera error:\n{exc}")
        finally:
            if self._camera is not None:
                self._schedule_poll()

    def _draw(self, image, detection_frame: DetectionFrame | None) -> None:
        canvas = self._canvas
        if canvas is None:
            return

        try:
            from PIL import Image, ImageTk
            import cv2
        except ModuleNotFoundError as exc:
            raise RuntimeError("Pillow and OpenCV are required for the VISION screen") from exc

        canvas.update_idletasks()
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        image_h, image_w = image.shape[:2]
        scale = min(width / image_w, height / image_h)
        draw_w = max(1, int(image_w * scale))
        draw_h = max(1, int(image_h * scale))
        offset_x = (width - draw_w) // 2
        offset_y = (height - draw_h) // 2

        resized = cv2.resize(image, (draw_w, draw_h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self._photo = photo

        canvas.delete("all")
        canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=photo)

        if detection_frame is None:
            return

        for detection in detection_frame.detections:
            x1 = offset_x + int(detection.x * draw_w)
            y1 = offset_y + int(detection.y * draw_h)
            x2 = x1 + int(detection.width * draw_w)
            y2 = y1 + int(detection.height * draw_h)
            canvas.create_rectangle(x1, y1, x2, y2, outline="#00ff77", width=2)
            label = f"{detection.label.upper()} {detection.confidence:.0%}"
            canvas.create_text(
                x1 + 4, max(offset_y + 8, y1 - 4),
                text=label, anchor=tk.SW, fill="#00ff77",
                font=("Sans", 9, "bold"),
            )

    def _set_mode(self, mode: CameraMode) -> None:
        self._processor.set_mode(mode)
        if mode is CameraMode.DAY:
            self._hardware_controls.apply(V4L2CameraProfile.DAY)
        elif mode is CameraMode.LOW_LIGHT:
            self._hardware_controls.apply(V4L2CameraProfile.LOW_LIGHT)
        self._update_mode_label()

    def _sync_hardware_profile(self) -> None:
        effective = self._processor.last_effective_mode
        target = (
            V4L2CameraProfile.LOW_LIGHT
            if effective is CameraMode.LOW_LIGHT
            else V4L2CameraProfile.DAY
        )
        self._hardware_controls.apply(target)

    def _toggle_ai(self) -> None:
        self._ai_enabled = not self._ai_enabled
        if not self._ai_enabled:
            self._last_detection = None
        self._update_status()

    def _update_mode_label(self) -> None:
        label = self._mode_label
        if label is None:
            return
        requested = self._processor.mode.value.upper().replace("_", " ")
        effective = self._processor.last_effective_mode.value.upper().replace("_", " ")
        text = f"Mode: {requested}" if self._processor.mode is not CameraMode.AUTO else f"Mode: AUTO → {effective}"
        label.configure(text=text)

    def _update_status(self) -> None:
        label = self._status_label
        if label is None:
            return
        detection = self._last_detection if self._ai_enabled else None
        latency = 0.0 if detection is None else detection.inference_time_ms
        objects = 0 if detection is None else len(detection.detections)
        self._update_mode_label()
        hardware = self._hardware_controls.current_profile
        hardware_name = "--" if hardware is None else hardware.value.upper().replace("_", " ")
        label.configure(
            text=(
                f"CAM {self._camera_fps:4.1f} fps\n"
                f"AI  {'ON ' if self._ai_enabled else 'OFF'} {self._ai_fps:4.1f} fps\n"
                f"INF {latency:4.0f} ms\n"
                f"OBJ {objects}\n"
                f"LUM {self._processor.last_luminance:4.0f}\n"
                f"HW  {hardware_name}\n"
                f"SRC {self._device}"
            )
        )
