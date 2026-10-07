# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Model readiness checks performed before the UI event loop starts."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class YoloModelReadiness:
    """Ensure the configured Ultralytics model is available locally."""

    def __init__(self, model_name: str = "yolo11n.pt") -> None:
        self._model_name = model_name
        self._model: Any | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model(self) -> Any:
        if self._model is None:
            raise RuntimeError("YOLO model has not been prepared")
        return self._model

    def prepare(self) -> Any:
        """Load the model now, triggering any first-run download before Tk starts."""
        if self._model is not None:
            return self._model

        try:
            from ultralytics import YOLO
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Ultralytics is required for VISION; run "
                "./development/debian/setup_camera_perception.sh"
            ) from exc

        # Ultralytics resolves named weights such as yolo11n.pt and downloads
        # them when missing. Doing that here keeps network/disk work out of the
        # Tk callback that activates VISION.
        self._model = YOLO(self._model_name)
        return self._model

    def local_file_exists(self) -> bool:
        """Return whether a path-like model name already exists locally."""
        path = Path(self._model_name).expanduser()
        return path.is_file()
