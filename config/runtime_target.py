# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Runtime target detection shared by application composition."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path


class RuntimeTarget(str, Enum):
    """Supported OpenRoadCode deployment targets."""

    LINUX_DEV = "linux-dev"
    RPI4 = "rpi4"
    RPI5 = "rpi5"


def detect_runtime_target(
    *,
    model_path: str | Path = "/proc/device-tree/model",
) -> RuntimeTarget:
    """Detect the deployment target, honoring an explicit override.

    @param model_path Raspberry Pi device-tree model path.
    @return Detected or explicitly selected runtime target.
    @exception ValueError if `OPENROAD_RUNTIME_TARGET` is unsupported.
    """
    override = os.getenv("OPENROAD_RUNTIME_TARGET")
    if override:
        try:
            return RuntimeTarget(override.strip().lower())
        except ValueError as exc:
            supported = ", ".join(target.value for target in RuntimeTarget)
            raise ValueError(
                f"Unsupported OPENROAD_RUNTIME_TARGET '{override}'; "
                f"expected one of: {supported}"
            ) from exc

    path = Path(model_path)
    try:
        model = path.read_text(encoding="utf-8").rstrip("\0")
    except OSError:
        return RuntimeTarget.LINUX_DEV
    if "Raspberry Pi 4" in model or "Compute Module 4" in model:
        return RuntimeTarget.RPI4
    if any(
        name in model
        for name in ("Raspberry Pi 5", "Raspberry Pi 500", "Compute Module 5")
    ):
        return RuntimeTarget.RPI5
    return RuntimeTarget.LINUX_DEV
