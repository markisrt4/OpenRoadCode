# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Optional

from protocols.rigctl import RigctlClient

from ..radio_backend_if import RadioBackendIf


class RigctlCommandError(RuntimeError):
    """An explicit command rejection with a safe numeric Hamlib error code."""

    def __init__(self, code: int) -> None:
        self.code = code
        super().__init__(f"Rigctl rejected command with code {code}")


class RigctlRadioBackend(RadioBackendIf):
    """Adapt the rigctl protocol client to the radio backend contract."""

    def __init__(self, client: RigctlClient) -> None:
        self._client = client

    def start(self) -> str:
        return self._checked_response(self._client.start())

    def stop(self) -> str:
        return self._checked_response(self._client.stop())

    def set_frequency(self, frequency_hz: int) -> str:
        return self._checked_response(self._client.set_frequency(frequency_hz))

    def get_frequency(self) -> int:
        response = self._client.get_frequency().strip()

        try:
            return int(response)
        except ValueError as exc:
            raise RuntimeError(f"rigctl returned an invalid frequency: {response!r}") from exc

    def set_mode(self, mode: str, bandwidth: int) -> str:
        return self._checked_response(self._client.set_mode(mode, bandwidth))

    def get_signal_strength(self) -> Optional[str]:
        return self._normalize_optional_response(self._client.get_signal_strength())

    def get_snr(self) -> Optional[str]:
        return self._normalize_optional_response(self._client.get_snr())

    def get_rds(self) -> Optional[str]:
        return self._normalize_optional_response(self._client.get_rds())

    @staticmethod
    def _checked_response(response: str) -> str:
        if isinstance(response, str) and not response.strip():
            raise TimeoutError("Rigctl command acknowledgement timed out")
        if isinstance(response, str) and response.strip().startswith("RPRT"):
            try:
                code = int(response.strip().split()[1])
            except (IndexError, ValueError) as error:
                raise RuntimeError("Rigctl returned an invalid acknowledgement") from error
            if code != 0:
                raise RigctlCommandError(code)
        return response

    @staticmethod
    def _normalize_optional_response(
        response: Optional[str],
    ) -> Optional[str]:
        """Normalize an optional rigctl response.

        Empty or whitespace-only responses are treated as unavailable.
        """

        if response is None:
            return None

        value = response.strip()
        return value or None


# Temporary compatibility alias while existing call sites migrate.
RigctlBackend = RigctlRadioBackend


__all__ = [
    "RigctlBackend",
    "RigctlRadioBackend",
    "RigctlCommandError",
]
