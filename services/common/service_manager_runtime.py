# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Runtime selection for the OpenRoadCode service supervisor backend."""

from __future__ import annotations

from collections.abc import Mapping
import os
import sys
from typing import Literal


ServiceManagerRuntime = Literal["termux", "linux"]


def detect_service_manager_runtime(
    environment: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
) -> ServiceManagerRuntime:
    """Return the service-manager runtime for the current host.

    Termux is identified from its environment rather than from the presence of
    a particular supervisor executable. Normal Linux hosts use systemd.
    """

    env = os.environ if environment is None else environment
    host_platform = sys.platform if platform is None else platform
    prefix = env.get("PREFIX", "")

    if env.get("TERMUX_VERSION") or prefix.startswith(
        "/data/data/com.termux/files/usr"
    ):
        return "termux"
    if host_platform.startswith("linux"):
        return "linux"
    raise RuntimeError(
        f"Unsupported OpenRoadCode service-manager runtime: {host_platform}"
    )


def create_service_manager(
    environment: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
):
    """Construct the supervisor backend appropriate for the current runtime."""

    runtime = detect_service_manager_runtime(environment, platform=platform)
    if runtime == "termux":
        from services.termux.service_manager import RunitServiceManager

        return RunitServiceManager()

    from services.linux.systemd_service_manager import SystemdServiceManager

    return SystemdServiceManager()
