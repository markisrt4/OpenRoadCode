# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Hardware-independent REST adapter for libSDRForge's v1 control API."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..radio_backend_if import RadioBackendIf


class SdrForgeRestRadioBackend(RadioBackendIf):
    """Control an existing SDRForge service; does not own the USB receiver."""

    def __init__(self, base_url: str = "http://127.0.0.1:5570", timeout: float = 1.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _request(self, path: str, body: dict[str, object] | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            self._base_url + path,
            data=data,
            headers={"Content-Type": "application/json"} if data is not None else {},
            method="POST" if data is not None else "GET",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                result = json.load(response)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise RuntimeError(f"SDRForge REST request failed ({path}): {exc}") from exc
        if not isinstance(result, dict):
            raise RuntimeError("SDRForge REST response must be a JSON object")
        return result

    def health(self) -> bool:
        return self._request("/v1/health").get("status") == "ok"

    def receiver_status(self) -> dict:
        return self._request("/v1/receiver")

    def start(self) -> object:
        return self._request("/v1/receiver/start", {})

    def stop(self) -> object:
        return self._request("/v1/receiver/stop", {})

    def set_frequency(self, frequency_hz: int) -> object:
        if frequency_hz <= 0:
            raise ValueError("frequency_hz must be positive")
        return self._request("/v1/receiver/frequency", {"frequency_hz": frequency_hz})

    def get_frequency(self) -> int:
        return int(self.receiver_status()["frequency_hz"])

    def set_mode(self, mode: str, bandwidth: int) -> object:
        return self._request("/v1/receiver/mode", {
            "mode": mode.upper(), "bandwidth_hz": bandwidth,
        })

    def get_signal_strength(self) -> float | str | None:
        return self.receiver_status().get("signal_strength")

    def get_snr(self) -> float | str | None:
        return self.receiver_status().get("snr")

    def get_rds(self) -> str | None:
        return self.receiver_status().get("rds")
