# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Hardware-independent REST adapter for libSDRForge's v1 control API."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..radio_backend_if import RadioBackendIf
from ..sdrforge_readiness import wait_for_sdrforge_ready


@dataclass(frozen=True, slots=True)
class SdrForgeConnectionDiagnostics:
    """Snapshot of the REST connection, suitable for diagnostics UI."""

    state: str
    reconnect_attempts: int
    reconnect_successes: int
    last_success_monotonic: float | None
    last_error: str | None


class SdrForgeRestRadioBackend(RadioBackendIf):
    """Control an existing SDRForge service; does not own the USB receiver."""

    def __init__(self, base_url: str = "http://127.0.0.1:5570", timeout: float = 1.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._connection_state = "unknown"
        self._reconnect_attempts = 0
        self._reconnect_successes = 0
        self._last_success_monotonic: float | None = None
        self._last_error: str | None = None

    def connection_diagnostics(self) -> SdrForgeConnectionDiagnostics:
        """Return an immutable connection snapshot without issuing network requests."""
        return SdrForgeConnectionDiagnostics(
            state=self._connection_state,
            reconnect_attempts=self._reconnect_attempts,
            reconnect_successes=self._reconnect_successes,
            last_success_monotonic=self._last_success_monotonic,
            last_error=self._last_error,
        )

    def _request(self, path: str, body: dict[str, object] | None = None) -> dict:
        # Read-only requests may be retried after a transient restart. A POST
        # may have succeeded before its response was lost: never replay it.
        if body is None and path != "/v1/health":
            try:
                return self._request_once(path, body)
            except RuntimeError as exc:
                if not isinstance(exc.__cause__, (URLError, TimeoutError, OSError)):
                    raise
                self._reconnect_attempts += 1
                self._connection_state = "reconnecting"
                try:
                    self.wait_until_ready(timeout=3.0)
                    result = self._request_once(path, body)
                except (RuntimeError, OSError) as recovery_error:
                    self._connection_state = "unavailable"
                    self._last_error = str(recovery_error)
                    raise
                self._reconnect_successes += 1
                return result
        return self._request_once(path, body)

    def _request_once(self, path: str, body: dict[str, object] | None = None) -> dict:
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
            self._connection_state = "unavailable"
            self._last_error = str(exc)
            raise RuntimeError(f"SDRForge REST request failed ({path}): {exc}") from exc
        if not isinstance(result, dict):
            self._connection_state = "unavailable"
            self._last_error = "SDRForge REST response must be a JSON object"
            raise RuntimeError(self._last_error)
        self._connection_state = "connected"
        self._last_success_monotonic = time.monotonic()
        self._last_error = None
        return result

    def wait_until_ready(self, timeout: float = 10.0) -> None:
        """Wait for REST readiness; never replay control commands."""
        wait_for_sdrforge_ready(self._base_url, timeout=timeout)

    def health(self) -> bool:
        try:
            return self._request("/v1/health").get("status") == "ok"
        except RuntimeError:
            return False

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
        return self._request(
            "/v1/receiver/mode",
            {
                "mode": mode.upper(),
                "bandwidth_hz": bandwidth,
            },
        )

    def get_signal_strength(self) -> float | str | None:
        return self.receiver_status().get("signal_strength")

    def get_snr(self) -> float | str | None:
        return self.receiver_status().get("snr")

    def get_rds(self) -> str | None:
        return self.receiver_status().get("rds")
