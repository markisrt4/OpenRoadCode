# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-level SDR++ controls used by orcUi."""

from __future__ import annotations

from protocols.sdrpp_remote_control import SDRPPRemoteControlClient


class OrcUiSdrppControl:
    """Expose ORC-oriented controls without leaking the remote protocol into UI code."""

    def __init__(self, client: SDRPPRemoteControlClient | None = None) -> None:
        self._client = client or SDRPPRemoteControlClient()

    def waterfall_visible(self) -> bool:
        """Return whether SDR++ is currently showing its waterfall."""
        return self._client.get_waterfall()

    def set_waterfall_visible(self, visible: bool) -> bool:
        """Show or hide the SDR++ waterfall immediately."""
        return self._client.set_waterfall(visible)

    def toggle_waterfall(self) -> bool:
        """Toggle the SDR++ waterfall and return its new visible state."""
        return self._client.toggle_waterfall()
