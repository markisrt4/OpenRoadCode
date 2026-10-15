# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Resolve ORC's isolated raster tools without changing the process environment."""
import os
import shutil
from pathlib import Path

from common.xdg_paths import openroadcode_data_dir

TOOLS = ("gdalinfo", "gdal_translate", "gdalwarp")


def gdal_tool(name: str) -> str:
    """Prefer one complete ORC installation, then the platform's packaged tools."""
    if name not in TOOLS:
        raise ValueError(f"Unsupported GDAL tool: {name}")
    override = os.environ.get("OPENROAD_GDAL_ROOT")
    root = Path(override) if override else openroadcode_data_dir("tools", "gdal", "current")
    if override or root.exists() or root.is_symlink():
        if not all((root / "bin" / tool).is_file() and os.access(root / "bin" / tool, os.X_OK)
                   for tool in TOOLS):
            raise RuntimeError(f"ORC GDAL installation is incomplete: {root}. Rerun development/termux/build_weather_gdal.sh")
        return str(root / "bin" / name)
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError("HRRR needs GDAL; install GDAL or run development/termux/build_weather_gdal.sh in Termux")
    return executable
