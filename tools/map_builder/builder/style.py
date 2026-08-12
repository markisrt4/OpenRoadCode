"""Style installation helpers."""

from __future__ import annotations

import json
from pathlib import Path


def install_style(template: Path, destination: Path) -> None:
    data = json.loads(template.read_text(encoding="utf-8"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
