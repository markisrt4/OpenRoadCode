# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Resolve the local Vision model and load its weights on demand."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.logging.diagnostics import ComponentLog, diagnostic_action
from common.xdg_paths import openroadcode_data_dir


def vision_model_path() -> Path:
    """Return the path shared by the installer and Vision."""
    return openroadcode_data_dir("vision", "models", "yolo11n.pt")


class YoloModelReadiness:
    """Ensure the configured Ultralytics model is available locally."""

    def __init__(self, model_name: str | None = None) -> None:
        self._diagnostics = ComponentLog("vision.model", "vision")
        self._model_name = model_name if model_name is not None else str(vision_model_path())
        self._model: Any | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model(self) -> Any:
        if self._model is None:
            raise RuntimeError("YOLO model has not been prepared")
        return self._model

    @diagnostic_action("model_load")
    def prepare(self) -> Any:
        """Load the local weights without a network download."""
        if self._model is not None:
            return self._model

        path = Path(self._model_name).expanduser()
        if not path.is_file():
            raise RuntimeError(
                f"Vision model missing at {path}. "
                "Run the host installer with --feature video-perception."
            )

        try:
            from ultralytics import YOLO
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Ultralytics is required for VISION; run "
                "./development/debian/setup_camera_perception.sh"
            ) from exc

        self._model = YOLO(str(path.resolve()))
        self._diagnostics.changed("model", "ready")
        return self._model

    def local_file_exists(self) -> bool:
        """Return whether a path-like model name already exists locally."""
        path = Path(self._model_name).expanduser()
        return path.is_file()
