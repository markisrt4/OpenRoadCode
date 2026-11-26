# SPDX-License-Identifier: MIT
"""Asynchronous SDRForge receiver configuration REST adapter."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from urllib import request

from protocols.sdrforge_control import authorize_local_sdrforge_request
from ui.radio.rf_hardware_config_if import RfHardwareConfig, RfHardwareConfigIf
from ui.ui_dispatcher_if import UiDispatcherIf


class SdrForgeRfHardwareConfig(RfHardwareConfigIf):
    """Perform receiver configuration I/O away from the presentation thread."""

    def __init__(self, dispatcher: UiDispatcherIf, endpoint: str = "http://127.0.0.1:5570") -> None:
        self._dispatcher = dispatcher
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
                gain = payload.get("gain_db")
                config: RfHardwareConfig = {
                    "sample_rate_hz": int(payload.get("sample_rate_hz", 2400000)),
                    "gain_db": float(gain) if gain is not None else None,
                    "ppm_correction": int(payload.get("ppm_correction", 0)),
                    "rtl_agc_enabled": bool(payload.get("rtl_agc_enabled", False)),
                }
            except (OSError, ValueError, TypeError, OverflowError) as exc:
                message = str(exc)
                self._dispatcher.dispatch_ui(lambda: on_error(message))
            else:
                self._dispatcher.dispatch_ui(lambda: on_success(config))

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
                with request.urlopen(
                    authorize_local_sdrforge_request(operation), timeout=5.0
                ) as response:
                    response.read()
            except (OSError, ValueError, TypeError, OverflowError) as exc:
                message = str(exc)
                self._dispatcher.dispatch_ui(lambda: on_error(message))
            else:
                self._dispatcher.dispatch_ui(on_success)

        threading.Thread(target=worker, name="orc-rf-config", daemon=True).start()
