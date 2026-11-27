# SPDX-License-Identifier: MIT
"""Local persistence for RF display preferences."""

import json
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile

from ui.radio.radio_visualization_config import RadioRenderer, RadioVisualizationConfig


class JsonRadioVisualizationSettings:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".config" / "openroadcode" / "rf_visualization.json"

    def load(self, defaults: RadioVisualizationConfig | None = None) -> RadioVisualizationConfig:
        fallback = defaults or RadioVisualizationConfig()
        try:
            values = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(values, dict):
                return RadioVisualizationConfig(
                    renderer=RadioRenderer(values.get("renderer", fallback.renderer)),
                    waterfall_rows=int(values.get("waterfall_rows", fallback.waterfall_rows)),
                    max_fps=int(values.get("max_fps", fallback.max_fps)),
                    palette=str(values.get("palette", fallback.palette)),
                )
        except (OSError, TypeError, ValueError, OverflowError):
            pass
        return fallback

    def save(self, config: RadioVisualizationConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self._path.parent, delete=False
        ) as output:
            temporary_path = Path(output.name)
            try:
                json.dump(asdict(config), output, indent=2)
                output.write("\n")
                output.close()
                temporary_path.replace(self._path)
            finally:
                temporary_path.unlink(missing_ok=True)
