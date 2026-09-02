# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application-level SDR++ controls used by orcUi."""

from __future__ import annotations

from protocols.sdrpp_remote_control import SDRPPRemoteControlClient


class OrcUiSdrppControl:
    """Expose ORC-oriented controls without leaking the remote protocol into UI code."""

    def __init__(self, client: SDRPPRemoteControlClient | None = None) -> None:
        self._client = client or SDRPPRemoteControlClient()

    def waterfall_visible(self) -> bool: return self._client.get_waterfall()
    def set_waterfall_visible(self, visible: bool) -> bool: return self._client.set_waterfall(visible)
    def toggle_waterfall(self) -> bool: return self._client.toggle_waterfall()
    def bandplan_visible(self) -> bool: return self._client.get_bandplan()
    def set_bandplan_visible(self, visible: bool) -> bool: return self._client.set_bandplan(visible)
    def toggle_bandplan(self) -> bool: return self._client.toggle_bandplan()
    def fft_hold_enabled(self) -> bool: return self._client.get_fft_hold()
    def set_fft_hold_enabled(self, enabled: bool) -> bool: return self._client.set_fft_hold(enabled)
    def toggle_fft_hold(self) -> bool: return self._client.toggle_fft_hold()
    def auto_range(self) -> bool: return self._client.auto_range()

    def theme(self) -> str: return self._client.get_theme()
    def themes(self) -> tuple[str, ...]: return self._client.get_themes()
    def set_theme(self, theme: str) -> bool: return self._client.set_theme(theme)
