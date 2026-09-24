# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Resolve runtime-wide environment shared across OpenRoadCode subsystems."""

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Mapping

ANDROID_BRIDGE_URL_ENV = "OPENROADCODE_ANDROID_BRIDGE_URL"
RUNTIME_ENV_FILE_ENV = "OPENROADCODE_RUNTIME_ENV_FILE"
DEFAULT_RUNTIME_ENV_FILE = Path(
    "/var/lib/openroadcode/service-profiles/openroadcode-runtime.env"
)


def android_bridge_url(
    configured: str,
    *,
    environment: Mapping[str, str] | None = None,
    runtime_environment_file: str | Path | None = None,
) -> str:
    """Resolve the shared Android Bridge endpoint, then fall back to config."""
    env = os.environ if environment is None else environment
    override = env.get(ANDROID_BRIDGE_URL_ENV, "").strip()
    if override:
        return override

    path = Path(
        runtime_environment_file
        or env.get(RUNTIME_ENV_FILE_ENV, "")
        or DEFAULT_RUNTIME_ENV_FILE
    )
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, PermissionError, OSError):
        return configured

    prefix = f"{ANDROID_BRIDGE_URL_ENV}="
    for line in lines:
        if not line.startswith(prefix):
            continue
        value = line.removeprefix(prefix).strip().strip('"').strip("'")
        if value:
            return value
    return configured
