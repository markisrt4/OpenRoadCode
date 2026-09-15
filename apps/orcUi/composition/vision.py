# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose the isolated camera/perception destination."""

from __future__ import annotations

from dataclasses import dataclass

from apps.orcUi.frontend.tk.camera_vision_screen import CameraVisionScreen
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from controllers.computer_vision.model_readiness import YoloModelReadiness


@dataclass(slots=True)
class VisionComposition:
    """Own the VISION screen and its transient camera/perception runtime."""

    screen: CameraVisionScreen
    model_readiness: YoloModelReadiness

    def prepare(self) -> None:
        """Prepare model assets before the Tk event loop starts."""
        self.model_readiness.prepare()

    def close(self) -> None:
        """Release camera and inference resources if the screen is active."""
        self.screen.hide()


def configure_vision(app: OrcUiApp) -> VisionComposition:
    """Create and register the isolated VISION destination."""
    readiness = YoloModelReadiness("yolo11n.pt")
    model = readiness.prepare()
    screen = CameraVisionScreen(
        app,
        theme_bundle=lambda: theme_bundle(app.theme_mode),
        model_name=readiness.model_name,
        prepared_model=model,
    )
    app.register_screen("VISION", screen, before="CONTROLS")
    return VisionComposition(screen=screen, model_readiness=readiness)
