# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the isolated camera/perception destination."""

from __future__ import annotations

from dataclasses import dataclass

from apps.orcUi.frontend.tk.camera_vision_screen import CameraVisionScreen
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from controllers.computer_vision.byte_track_object_tracker import ByteTrackObjectTracker
from controllers.computer_vision.camera_frame_processor import CameraFrameProcessor
from controllers.computer_vision.model_readiness import YoloModelReadiness
from controllers.computer_vision.perception_worker import PerceptionWorker
from controllers.computer_vision.vision_controller import VisionController
from controllers.computer_vision.yolo_object_detector import YoloObjectDetector
from hardware_io.camera.v4l2_camera import V4L2Camera
from hardware_io.camera.v4l2_camera_controls import V4L2CameraProfileController


@dataclass(slots=True)
class VisionComposition:
    """Own the VISION screen and its transient camera/perception runtime."""

    screen: CameraVisionScreen
    controller: VisionController
    model_readiness: YoloModelReadiness

    def prepare(self) -> None:
        """Prepare model assets before the Tk event loop starts."""
        self.model_readiness.prepare()

    def close(self) -> None:
        """Release camera and inference resources if the screen is active."""
        self.controller.close()


def configure_vision(app: OrcUiApp) -> VisionComposition:
    """Create and register the isolated VISION destination."""
    readiness = YoloModelReadiness("yolo11n.pt")
    model = readiness.prepare()
    screen = CameraVisionScreen(
        app,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )
    detector = YoloObjectDetector(
        readiness.model_name,
        confidence=0.10,
        image_size=640,
        model=model,
    )
    controller = VisionController(
        app,
        screen,
        V4L2Camera("/dev/video0", width=1920, height=1080, fps=30.0, pixel_format="MJPG"),
        V4L2CameraProfileController("/dev/video0"),
        CameraFrameProcessor(),
        PerceptionWorker(detector, ByteTrackObjectTracker(frame_rate=30)),
        source_label="/dev/video0",
    )
    app.register_screen("VISION", screen, before="CONTROLS")
    return VisionComposition(
        screen=screen,
        controller=controller,
        model_readiness=readiness,
    )
