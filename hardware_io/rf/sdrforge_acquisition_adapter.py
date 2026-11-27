# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""REST acquisition adapter for a managed SDRForge service."""

import json
import time
from collections.abc import Callable
from urllib.request import Request, urlopen

from hardware_io.rf.receiver_discovery_if import ReceiverDevice


class SdrforgeAcquisitionAdapter:
    """Select a receiver and confirm acquisition or release via REST."""

    def __init__(
        self,
        token: str,
        base_url: str = "http://127.0.0.1:5570",
        timeout: float = 35.0,
        *,
        ensure_ready: Callable[[], None] | None = None,
    ) -> None:
        if not token or timeout <= 0:
            raise ValueError("credential and positive timeout required")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._ensure_ready = ensure_ready
        self._start_requested = False

    def _request(self, path: str, body: dict[str, object] | None = None) -> dict[str, object]:
        request = Request(
            self._base_url + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        if body is not None:
            request.add_unredirected_header("X-SDRForge-Acquisition-Token", self._token)
        with urlopen(request, timeout=min(2.0, self._timeout)) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("invalid SDRForge response")
        return result

    def start(self, device: ReceiverDevice) -> bool:
        """Start the selected receiver and wait for acquisition evidence."""
        if not device.identity:
            return False
        if self._ensure_ready is not None:
            self._ensure_ready()
        status = self._request("/v1/receiver")
        if status.get("running") is True or status.get("starting") is True:
            raise RuntimeError("SDRForge already has an active or starting receiver.")
        if "hardware_released" not in status:
            raise RuntimeError(
                "The running SDRForge service does not report hardware release. "
                "Install the pinned SDRForge build in the service's Python environment."
            )
        if not self._released(status):
            detail = status.get("release_error") or "hardware release is unconfirmed"
            raise RuntimeError(f"SDRForge cannot confirm receiver release: {detail}")
        self._request("/v1/rf/config", {"device_serial": device.serial})
        # Record the attempt before sending it: a lost reply can still mean
        # the service started acquisition.
        self._start_requested = True
        self._request("/v1/receiver/start", {})
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            status = self._request("/v1/receiver")
            if status.get("startup_error"):
                raise RuntimeError(f"SDRForge startup failed: {status['startup_error']}")
            if status.get("running") is True and status.get("starting") is False:
                config = self._request("/v1/rf/config")
                actual = config.get("device_serial")
                if actual != device.serial:
                    raise RuntimeError(
                        f"SDRForge reported receiver {actual!r}, expected {device.serial!r}."
                    )
                return True
            time.sleep(0.1)
        raise RuntimeError(f"SDRForge timed out starting receiver {device.serial}.")

    def active(self, device: ReceiverDevice) -> bool:
        """Check whether the configured receiver is still running."""
        try:
            status = self._request("/v1/receiver")
            return (
                status.get("running") is True
                and status.get("starting") is False
                and self._request("/v1/rf/config").get("device_serial") == device.serial
            )
        except (OSError, ValueError):
            return False

    def stop(self) -> bool:
        """Stop acquisition and wait for explicit release confirmation."""
        if not self._start_requested:
            return self._released(self._request("/v1/receiver"))
        if self._ensure_ready is not None:
            self._ensure_ready()
        self._request("/v1/receiver/stop", {})
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            status = self._request("/v1/receiver")
            if status.get("release_error"):
                return False
            if self._released(status):
                self._start_requested = False
                return True
            time.sleep(0.1)
        return False

    @staticmethod
    def _released(status: dict[str, object]) -> bool:
        return (
            status.get("running") is False
            and status.get("starting") is False
            and status.get("hardware_released") is True
            and not status.get("release_error")
        )
