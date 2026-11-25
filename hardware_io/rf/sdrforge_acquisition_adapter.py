# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""REST acquisition adapter for a managed SDRForge service."""

import json
import time
from urllib.request import Request, urlopen

from hardware_io.rf.receiver_discovery_if import ReceiverDevice


class SdrforgeAcquisitionAdapter:
    """Select a receiver and confirm acquisition or release via REST."""

    def __init__(
        self,
        token: str,
        base_url: str = "http://127.0.0.1:5570",
        timeout: float = 35.0,
    ) -> None:
        if not token or timeout <= 0:
            raise ValueError("credential and positive timeout required")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _request(
        self, path: str, body: dict[str, object] | None = None
    ) -> dict[str, object]:
        request = Request(
            self._base_url + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "X-SDRForge-Acquisition-Token": self._token,
            },
        )
        with urlopen(request, timeout=min(2.0, self._timeout)) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("invalid SDRForge response")
        return result

    def start(self, device: ReceiverDevice) -> bool:
        """Start the selected receiver and wait for acquisition evidence."""
        if not device.identity:
            return False
        status = self._request("/v1/receiver")
        if (
            status.get("running") is not False
            or status.get("starting") is not False
            or status.get("hardware_released") is not True
        ):
            return False
        self._request("/v1/rf/config", {"device_serial": device.serial})
        self._request("/v1/receiver/start", {})
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            status = self._request("/v1/receiver")
            if status.get("startup_error"):
                return False
            if status.get("running") is True and status.get("starting") is False:
                config = self._request("/v1/rf/config")
                return config.get("device_serial") == device.serial
            time.sleep(0.1)
        return False

    def stop(self) -> bool:
        """Stop acquisition and wait for explicit release confirmation."""
        self._request("/v1/receiver/stop", {})
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            status = self._request("/v1/receiver")
            if status.get("release_error"):
                return False
            if (
                status.get("running") is False
                and status.get("starting") is False
                and status.get("hardware_released") is True
            ):
                return True
            time.sleep(0.1)
        return False
