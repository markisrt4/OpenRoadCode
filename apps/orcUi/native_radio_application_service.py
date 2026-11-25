# SPDX-License-Identifier: MIT
"""Native SDRForge radio lifecycle without an SDR++ process or X11 client."""


class NativeRadioApplicationService:
    """Compatibility boundary for features sharing the RF application service."""

    fullscreen = False
    presented = False

    def present(self) -> None:
        """The native Tk receiver is already owned by the radio panel."""

    def window_process_id(self, *, timeout_seconds: float) -> int:
        raise RuntimeError("Native SDRForge has no external window process")

    def relinquish_for_adsb(self) -> None:
        """ADS-B arbitration is handled by the RF session and SDRForge service."""

    def close(self) -> None:
        """No external SDR++ process was started."""
