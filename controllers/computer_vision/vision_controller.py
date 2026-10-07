# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own camera capture and perception independently of GUI toolkits."""

from __future__ import annotations

import threading
import time

from controllers.computer_vision.camera_frame_processor import CameraFrameProcessor, CameraMode
from controllers.computer_vision.object_detector_if import DetectionFrame
from controllers.computer_vision.object_tracker_if import TrackFrame
from controllers.computer_vision.perception_worker import PerceptionWorker
from hardware_io.camera.camera_controls_if import CameraControlsIf, CameraProfile
from hardware_io.camera.camera_if import CameraFrame, CameraIf
from ui.ui_dispatcher_if import UiDispatcherIf
from ui.vision.vision_request_handler_if import VisionRequestHandlerIf
from ui.vision.vision_ui_if import VisionUiIf
from ui.vision.vision_ui_state import (
    VisionCameraMode,
    VisionImage,
    VisionLifecycle,
    VisionObject,
    VisionPixelFormat,
    VisionUiState,
)


class VisionController(VisionRequestHandlerIf):
    """Coordinate capture, preprocessing, inference, tracking, and UI state."""

    def __init__(
        self,
        dispatcher: UiDispatcherIf,
        ui: VisionUiIf,
        camera: CameraIf,
        controls: CameraControlsIf,
        processor: CameraFrameProcessor,
        worker: PerceptionWorker,
        *,
        source_label: str,
    ) -> None:
        self._dispatcher = dispatcher
        self._ui = ui
        self._camera = camera
        self._controls = controls
        self._processor = processor
        self._worker = worker
        self._source_label = source_label
        self._lock = threading.RLock()
        self._generation = 0
        self._active = False
        self._closed = False
        self._ai_enabled = True
        self._supported_profiles: frozenset[CameraProfile] | None = None
        self._hardware_status = ""
        self._thread: threading.Thread | None = None
        self._pending_delivery: tuple[int, VisionUiState] | None = None
        self._delivery_scheduled = False
        self._camera_rate_hz = 0.0
        self._inference_rate_hz = 0.0
        self._last_capture_time = 0.0
        self._last_inference_time = 0.0
        self._last_processed_count = 0
        self._ui.set_vision_request_handler(self)
        self._ui.set_vision_state(self._state(VisionLifecycle.INACTIVE))

    def request_activate(self) -> None:
        """Start a new camera session when one is not already active."""
        with self._lock:
            if self._closed or self._active:
                return
            self._generation += 1
            generation = self._generation
            self._active = True
            self._hardware_status = ""
            self._reset_metrics()
            thread = threading.Thread(
                target=self._run,
                args=(generation,),
                name="VisionController",
                daemon=True,
            )
            self._thread = thread
            self._publish(generation, self._state(VisionLifecycle.STARTING, "Starting camera…"))
            thread.start()

    def request_deactivate(self) -> None:
        """Stop the current session and invalidate all queued frame deliveries."""
        with self._lock:
            if not self._active:
                return
            self._active = False
            self._generation += 1
            generation = self._generation
            thread = self._thread
        self._camera.close()
        if thread is not None and thread is not threading.current_thread():
            thread.join()
        with self._lock:
            if self._thread is thread:
                self._thread = None
            if not self._closed:
                self._hardware_status = ""
                self._publish(generation, self._state(VisionLifecycle.INACTIVE))

    def request_camera_mode(self, mode: VisionCameraMode) -> None:
        """Apply a semantic processing mode to the current or next session.

        @param mode Desired processing mode.
        """
        selected = VisionCameraMode(mode)
        with self._lock:
            if self._closed:
                return
            if (
                selected is not VisionCameraMode.AUTO
                and self._supported_profiles is not None
                and CameraProfile(selected.value) not in self._supported_profiles
            ):
                return
            self._processor.set_mode(CameraMode(selected.value))
            self._publish(self._generation, self._state(self._lifecycle()))

    def request_ai_enabled(self, enabled: bool) -> None:
        """Set the desired inference state.

        @param enabled True to submit frames for inference.
        """
        with self._lock:
            if self._closed:
                return
            self._ai_enabled = bool(enabled)
            self._publish(self._generation, self._state(self._lifecycle()))

    def close(self) -> None:
        """Release transient resources and permanently disconnect the UI."""
        self.request_deactivate()
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._generation += 1
            self._pending_delivery = None
        self._ui.set_vision_request_handler(None)

    def _run(self, generation: int) -> None:
        try:
            self._camera.open()
            self._controls.invalidate()
            self._supported_profiles = self._controls.probe_supported_profiles()
            requested_profile = (
                None
                if self._processor.mode is CameraMode.AUTO
                else CameraProfile(self._processor.mode.value)
            )
            if (
                requested_profile is not None
                and requested_profile not in self._supported_profiles
            ):
                self._processor.set_mode(CameraMode.AUTO)
            self._controls.restore_day_defaults()
            self._worker.start()
            with self._lock:
                self._last_processed_count = self._worker.processed_frames
            status = ""
            if not self._supported_profiles:
                status = "Camera hardware profiles unavailable; using device defaults"
            self._hardware_status = status
            self._publish(generation, self._state(VisionLifecycle.RUNNING, status))
            while self._is_current(generation):
                frame = self._camera.read()
                if not self._is_current(generation):
                    break
                self._capture_frame(generation, frame)
        except Exception as exc:
            if self._is_current(generation):
                with self._lock:
                    self._active = False
                self._publish(
                    generation,
                    self._state(VisionLifecycle.ERROR, f"Camera unavailable: {exc}"),
                )
        finally:
            self._worker.stop()
            try:
                self._controls.restore_day_defaults()
            except RuntimeError:
                pass
            self._camera.close()
            with self._lock:
                if self._thread is threading.current_thread():
                    self._thread = None

    def _capture_frame(self, generation: int, frame: CameraFrame) -> None:
        now = time.perf_counter()
        with self._lock:
            elapsed = now - self._last_capture_time
            if self._last_capture_time > 0.0 and elapsed > 0.0:
                measured = 1.0 / elapsed
                self._camera_rate_hz = self._smooth(self._camera_rate_hz, measured, 0.1)
            self._last_capture_time = now
            processed = self._processor.process(frame.image)
            effective_mode = self._processor.last_effective_mode
            target_profile = (
                CameraProfile.LOW_LIGHT
                if effective_mode is CameraMode.LOW_LIGHT
                else CameraProfile.DAY
            )
            if self._supported_profiles is not None and target_profile in self._supported_profiles:
                self._controls.apply(target_profile)
            ai_enabled = self._ai_enabled

        processed_frame = CameraFrame(processed, frame.timestamp_s, frame.sequence)
        if ai_enabled:
            self._worker.submit(processed_frame)
        detection = self._worker.latest_result if ai_enabled else None
        tracks = self._worker.latest_tracks if ai_enabled else None
        self._update_inference_rate(now)
        image = self._to_ui_image(processed_frame)
        objects = self._objects(detection, tracks)
        latency_s = 0.0 if detection is None else detection.inference_time_ms / 1000.0
        self._publish(
            generation,
            self._state(
                VisionLifecycle.RUNNING,
                image=image,
                objects=objects,
                inference_latency_s=latency_s,
            ),
        )

    def _update_inference_rate(self, now: float) -> None:
        processed_count = self._worker.processed_frames
        with self._lock:
            if processed_count == self._last_processed_count:
                return
            elapsed = now - self._last_inference_time
            delta = processed_count - self._last_processed_count
            if self._last_inference_time > 0.0 and elapsed > 0.0 and delta > 0:
                measured = delta / elapsed
                self._inference_rate_hz = self._smooth(
                    self._inference_rate_hz, measured, 0.2
                )
            self._last_processed_count = processed_count
            self._last_inference_time = now

    def _state(
        self,
        lifecycle: VisionLifecycle,
        status_message: str = "",
        *,
        image: VisionImage | None = None,
        objects: tuple[VisionObject, ...] = (),
        inference_latency_s: float = 0.0,
    ) -> VisionUiState:
        with self._lock:
            if not status_message:
                status_message = self._hardware_status
            requested = VisionCameraMode(self._processor.mode.value)
            effective = VisionCameraMode(self._processor.last_effective_mode.value)
            luminance = max(0.0, min(1.0, self._processor.last_luminance / 255.0))
            return VisionUiState(
                lifecycle=lifecycle,
                requested_mode=requested,
                effective_mode=effective,
                available_modes=(VisionCameraMode.AUTO,) + tuple(
                    VisionCameraMode(profile.value)
                    for profile in (CameraProfile.DAY, CameraProfile.LOW_LIGHT)
                    if self._supported_profiles is None
                    or profile in self._supported_profiles
                ),
                ai_enabled=self._ai_enabled,
                camera_rate_hz=self._camera_rate_hz,
                inference_rate_hz=self._inference_rate_hz,
                inference_latency_s=inference_latency_s,
                luminance_ratio=luminance,
                source_label=self._source_label,
                status_message=status_message,
                image=image,
                objects=objects,
            )

    def _publish(self, generation: int, state: VisionUiState) -> None:
        with self._lock:
            if self._closed or generation != self._generation:
                return
            self._pending_delivery = (generation, state)
            if self._delivery_scheduled:
                return
            self._delivery_scheduled = True
        try:
            self._dispatcher.schedule_ui_callback(0, self._deliver_pending)
        except Exception:
            with self._lock:
                self._delivery_scheduled = False
            raise

    def _deliver_pending(self) -> None:
        with self._lock:
            pending = self._pending_delivery
            self._pending_delivery = None
            self._delivery_scheduled = False
            if pending is None:
                return
            generation, state = pending
            if self._closed or generation != self._generation:
                return
        self._ui.set_vision_state(state)

    def _is_current(self, generation: int) -> bool:
        with self._lock:
            return self._active and not self._closed and generation == self._generation

    def _lifecycle(self) -> VisionLifecycle:
        if self._closed or not self._active:
            return VisionLifecycle.INACTIVE
        return VisionLifecycle.RUNNING if self._camera.is_open else VisionLifecycle.STARTING

    def _reset_metrics(self) -> None:
        self._camera_rate_hz = 0.0
        self._inference_rate_hz = 0.0
        self._last_capture_time = 0.0
        self._last_inference_time = 0.0
        self._last_processed_count = self._worker.processed_frames

    @staticmethod
    def _smooth(previous: float, measured: float, weight: float) -> float:
        return measured if previous == 0.0 else (1.0 - weight) * previous + weight * measured

    @staticmethod
    def _to_ui_image(frame: CameraFrame) -> VisionImage:
        image = frame.image
        height, width = image.shape[:2]
        rgb_bytes = image[:, :, ::-1].tobytes()
        return VisionImage(
            width=width,
            height=height,
            stride_bytes=width * 3,
            pixel_format=VisionPixelFormat.RGB888,
            timestamp_s=frame.timestamp_s,
            sequence=frame.sequence,
            data=rgb_bytes,
        )

    @staticmethod
    def _objects(
        detection: DetectionFrame | None, tracks: TrackFrame | None
    ) -> tuple[VisionObject, ...]:
        if tracks is not None and tracks.tracks:
            return tuple(
                VisionObject(
                    label=track.label,
                    confidence=track.confidence,
                    x=track.x,
                    y=track.y,
                    width=track.width,
                    height=track.height,
                    track_id=track.track_id,
                    track_age_s=track.age_s,
                )
                for track in tracks.tracks
            )
        if detection is None:
            return ()
        return tuple(
            VisionObject(
                label=item.label,
                confidence=item.confidence,
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
            )
            for item in detection.detections
        )
