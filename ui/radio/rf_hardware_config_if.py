# SPDX-License-Identifier: MIT
"""Toolkit-independent asynchronous receiver hardware configuration contract."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypedDict


class RfHardwareConfig(TypedDict):
    """Receiver settings exchanged with the SDRForge REST API."""

    sample_rate_hz: int
    gain_db: float | None
    ppm_correction: int
    rtl_agc_enabled: bool


class RfHardwareConfigIf(Protocol):
    """Run RF requests asynchronously and deliver completions on the UI thread."""

    def load(
        self, on_success: Callable[[RfHardwareConfig], None], on_error: Callable[[str], None]
    ) -> None:
        """Request the current receiver configuration asynchronously.
        @param on_success Callback receiving the configuration.
        @param on_error Callback receiving an error message.
        """
        ...

    def apply(
        self,
        config: RfHardwareConfig,
        on_success: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Apply receiver configuration asynchronously.
        @param config Requested receiver settings.
        @param on_success Callback invoked on successful application.
        @param on_error Callback receiving an error message.
        """
        ...
