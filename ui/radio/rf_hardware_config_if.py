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
    """Complete asynchronous RF requests without blocking the UI thread."""

    def load(
        self, on_success: Callable[[RfHardwareConfig], None], on_error: Callable[[str], None]
    ) -> None: ...

    def apply(
        self,
        config: RfHardwareConfig,
        on_success: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None: ...
