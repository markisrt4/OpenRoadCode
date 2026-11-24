# SPDX-License-Identifier: MIT
"""Asynchronous SDRForge receiver configuration REST adapter."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from urllib import request
from urllib.error import HTTPError, URLError

from ui.radio.rf_hardware_config_if import RfHardwareConfig, RfHardwareConfigIf


class SdrForgeRfHardwareConfig(RfHardwareConfigIf):
    """Perform receiver configuration I/O away from the presentation thread."""

    def __init__(self, endpoint: str = "http://127.0.0.1:5570") -> None:
        self._url = endpoint.rstrip("/") + "/v1/rf/config"

    def load(
        self, on_success: Callable[[RfHardwareConfig], None], on_error: Callable[[str], None]
    ) -> None:
        def worker() -> None:
            try:
                with request.urlopen(self._url, timeout=3.0) as response:
                    payload = json.load(response)
                if not isinstance(payload, dict):
                    raise ValueError("Invalid receiver configuration response")
                on_success(payload)
            except (OSError, ValueError, TypeError) as exc:
                on_error(str(exc))

        threading.Thread(target=worker, name="orc-rf-config-read", daemon=True).start()

    def apply(
        self,
        config: RfHardwareConfig,
        on_success: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        def worker() -> None:
            try:
                payload = json.dumps(config).encode("utf-8")
                operation = request.Request(
                    self._url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with request.urlopen(operation, timeout=5.0) as response:
                    response.read()
                on_success()
            except (OSError, ValueError, TypeError) as exc:
                on_error(str(exc))

        threading.Thread(target=worker, name="orc-rf-config", daemon=True).start()
