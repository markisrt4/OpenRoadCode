# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Detect and apply graphics runtime hints for external applications."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GraphicsRuntime:
    """Describe the graphics backend selected for the current platform."""

    backend: str
    hardware_accelerated: bool
    environment: dict[str, str]


def detect_graphics_runtime(
    *,
    environment: dict[str, str] | None = None,
    hardware: str | None = None,
    platform: str | None = None,
    kgsl_present: bool | None = None,
    freedreno_icd_present: bool | None = None,
) -> GraphicsRuntime:
    """Detect a conservative graphics runtime configuration.

    The detector currently knows one validated Android/Termux hardware path:
    Qualcomm/Adreno through Freedreno/Turnip and Zink. Unknown devices are left
    untouched rather than guessing a vendor-specific driver.
    """
    source_environment = environment or os.environ
    prefix = source_environment.get("PREFIX", "")
    is_termux = prefix.startswith("/data/data/com.termux/files/usr")

    if not is_termux:
        return GraphicsRuntime("system", False, {})

    resolved_hardware = hardware if hardware is not None else _getprop("ro.hardware")
    resolved_platform = platform if platform is not None else _getprop("ro.board.platform")
    resolved_kgsl = kgsl_present if kgsl_present is not None else Path("/dev/kgsl-3d0").exists()
    resolved_icd = (
        freedreno_icd_present
        if freedreno_icd_present is not None
        else _freedreno_icd_present(prefix)
    )

    is_qualcomm = (
        resolved_hardware.startswith("qcom")
        or resolved_platform.startswith("qcom")
        or resolved_kgsl
    )

    if is_qualcomm and resolved_icd:
        return GraphicsRuntime(
            backend="freedreno-zink",
            hardware_accelerated=True,
            environment={"MESA_LOADER_DRIVER_OVERRIDE": "zink"},
        )

    return GraphicsRuntime("generic", False, {})


def graphics_environment(
    base_environment: dict[str, str],
    *,
    runtime: GraphicsRuntime | None = None,
) -> dict[str, str]:
    """Return a copy of an environment with selected graphics hints applied."""
    result = dict(base_environment)
    selected_runtime = runtime or detect_graphics_runtime(environment=result)
    result.update(selected_runtime.environment)
    return result


def _getprop(name: str) -> str:
    try:
        result = subprocess.run(
            ["getprop", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return result.stdout.strip()


def _freedreno_icd_present(prefix: str) -> bool:
    if not prefix:
        return False

    # Termux currently installs Vulkan ICD manifests under share/vulkan/icd.d.
    # Keep etc/vulkan/icd.d as a compatibility location because other Linux
    # layouts use it and package layouts are not an API worth betting on.
    icd_directories = (
        Path(prefix) / "share" / "vulkan" / "icd.d",
        Path(prefix) / "etc" / "vulkan" / "icd.d",
    )
    return any(
        any(icd_dir.glob("*freedreno*.json"))
        for icd_dir in icd_directories
    )
