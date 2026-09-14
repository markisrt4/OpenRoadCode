# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Installed-host policy shared by OpenRoadCode applications."""

from __future__ import annotations

import os
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 fallback used by supported venvs.
    import tomli as tomllib  # type: ignore[no-redef]

from common.xdg_paths import openroadcode_config_dir


_HOST_CONFIG = "host.toml"
_RPI_TARGETS = {"rpi4", "rpi5"}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def installed_target(config_path: str | Path | None = None) -> str | None:
    """Return the selected installation target, if one has been persisted."""
    environment_target = os.environ.get("OPENROAD_INSTALL_TARGET", "").strip().lower()
    if environment_target:
        return environment_target

    path = (
        Path(config_path).expanduser()
        if config_path is not None
        else openroadcode_config_dir(_HOST_CONFIG)
    )
    try:
        with path.open("rb") as stream:
            document = tomllib.load(stream)
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return None

    target = document.get("target")
    if not isinstance(target, str):
        return None
    normalized = target.strip().lower()
    return normalized or None


def orcui_fullscreen_default(config_path: str | Path | None = None) -> bool:
    """Resolve orcUi fullscreen policy, honoring an explicit environment override."""
    override = os.environ.get("ORCUI_FULLSCREEN")
    if override is not None:
        normalized = override.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
        raise ValueError(
            "ORCUI_FULLSCREEN must be one of: "
            "1/0, true/false, yes/no, or on/off"
        )

    return installed_target(config_path) in _RPI_TARGETS
