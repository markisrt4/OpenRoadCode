# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the isolated camera/perception destination."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from common.resource_cleanup import close_resources
from apps.orcUi.adapters.vision_navigation import VisionNavigationIngress, VisionNavigationUiAdapter
from controllers.computer_vision.navigation_overlay_controller import NavigationOverlayController

from apps.orcUi.frontend.tk.camera_vision_screen import CameraVisionScreen
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from apps.orcUi.composition.vision_camera import create_vision_camera
from controllers.computer_vision.byte_track_object_tracker import ByteTrackObjectTracker
from controllers.computer_vision.camera_frame_processor import CameraFrameProcessor
from controllers.computer_vision.model_readiness import YoloModelReadiness
from controllers.computer_vision.perception_worker import PerceptionWorker
from controllers.computer_vision.vision_controller import VisionController
from controllers.computer_vision.yolo_object_detector import LazyYoloObjectDetector
from ui.vision.vision_ui_state import VisionLifecycle, VisionUiState

_LOG = logging.getLogger(__name__)


@dataclass(slots=True)
class VisionComposition:
    """Own the VISION screen and its transient camera/perception runtime."""

    screen: CameraVisionScreen
    controller: VisionController | None
    model_readiness: YoloModelReadiness
    navigation: NavigationOverlayController | None = None
    ingress: VisionNavigationIngress | None = None

    def start(self) -> None:
        """Start navigation ingress without opening the camera or loading AI models."""
        if self.ingress is not None:
            self.ingress.start()

    def prepare(self) -> None:
        """Prepare model assets before the Tk event loop starts."""
        self.start()
        self.model_readiness.prepare()

    def close(self) -> None:
        """Release camera and inference resources if the screen is active."""
        close_resources(*(resource.close for resource in
                          (self.ingress, self.navigation, self.controller) if resource is not None))


def configure_vision(app: OrcUiApp) -> VisionComposition:
    """Create and register the isolated VISION destination."""
    readiness = YoloModelReadiness("yolo11n.pt")
    screen = CameraVisionScreen(
        app,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
    )
    navigation = NavigationOverlayController(app, screen)
    ingress = VisionNavigationIngress(navigation)
    try:
        camera, controls, source_label = create_vision_camera()
    except (RuntimeError, ImportError, OSError, ValueError) as exc:
        # An invalid camera configuration disables this optional destination.
        # AI availability is handled separately below so live video can continue.
        _LOG.warning("VISION unavailable: %s", exc)
        screen.set_vision_state(VisionUiState(
            lifecycle=VisionLifecycle.ERROR, ai_enabled=False,
            status_message=f"VISION unavailable: {exc}",
        ))
        app.register_screen("VISION", screen, before="CONTROLS")
        return VisionComposition(screen=screen, controller=None, model_readiness=readiness,
                                 navigation=navigation, ingress=ingress)
    worker = None
    prepare_model = None
    ai_reason = ""
    try:
        detector = LazyYoloObjectDetector(readiness, confidence=0.10, image_size=640)
        tracker = ByteTrackObjectTracker(frame_rate=30)
        worker = PerceptionWorker(detector, tracker)
        prepare_model = detector.prepare
    except (RuntimeError, ImportError, OSError, ValueError) as exc:
        _LOG.warning("VISION AI unavailable; live camera remains available: %s", exc)
        ai_reason = str(exc)
    controller = VisionController(
        app,
        VisionNavigationUiAdapter(screen, navigation),
        camera,
        controls,
        CameraFrameProcessor(),
        worker,
        source_label=source_label,
        prepare_model=prepare_model,
        ai_unavailable_reason=ai_reason,
    )
    app.register_screen("VISION", screen, before="CONTROLS")
    return VisionComposition(
        screen=screen,
        controller=controller,
        model_readiness=readiness,
        navigation=navigation,
        ingress=ingress,
    )
