# SPDX-License-Identifier: MIT
"""Start the installed SDRForge transports for one receiver assignment."""

from __future__ import annotations

import subprocess

from controllers.radio.sdrforge_readiness import wait_for_sdrforge_ready


class SdrForgeSystemdInstance:
    """Start a fixed user unit on demand and wait for its REST transport."""

    def __init__(self, unit: str, rest_url: str) -> None:
        self._unit = unit
        self._rest_url = rest_url

    def ensure_ready(self) -> None:
        result = subprocess.run(
            ["systemctl", "--user", "--no-ask-password", "start", self._unit],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Cannot start {self._unit}: {result.stderr.strip()}")
        wait_for_sdrforge_ready(self._rest_url, timeout=5)
