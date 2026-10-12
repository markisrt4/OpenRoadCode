# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Own automatic network recovery and discard stale internet probe results."""
from queue import SimpleQueue, Empty
from threading import Thread
from controllers.connectivity.internet_access import internet_reachable
from controllers.connectivity.network_monitor import NetworkMonitor


class ShellConnectivityController:
    """Observe network reachability and publish mode on the UI dispatcher."""

    def __init__(self, mode, dispatcher, paint, set_status):
        self.online_mode = mode
        self._dispatcher = dispatcher
        self._paint = paint
        self._set_status = set_status
        self._closing = False
        self._callback_id = None
        self._internet_status: bool | None = None
        self._internet_results = SimpleQueue()
        self._internet_generation = 0
        self._internet_probe_active = False
        self._internet_next_probe = 0
        self._network_available: bool | None = None
        self._network_results = SimpleQueue()
        self._network_monitor = NetworkMonitor(self._network_results.put)

    def start(self):
        """Start bounded network monitoring and scheduled presentation."""
        self._network_monitor.start()
        self._poll_internet_status()

    def close(self):
        """Stop network monitoring and reject all late probe completions."""
        self._closing = True
        self._network_monitor.close()
        if self._callback_id is not None:
            self._dispatcher.cancel_ui_callback(self._callback_id)
            self._callback_id = None

    def toggle(self):
        """Request the opposite saved internet preference."""
        self._toggle_online_mode()

    def _toggle_online_mode(self) -> None:
        try:
            if not self.online_mode.requested_online and self._network_available is False:
                self.online_mode.set_reachable(False)
            self.online_mode.set_online(not self.online_mode.requested_online)
        except OSError as exc:
            self._set_status(f"Could not save online mode: {exc}")
            return
        self._internet_generation += 1
        self._internet_status = None
        self._internet_next_probe = 0
        self._paint_online_mode()

    def _paint_online_mode(self) -> None:
        self._paint(self.online_mode.online, self._internet_status)

    def _poll_internet_status(self) -> None:
        if self._closing:
            return
        while True:
            try:
                available = self._network_results.get_nowait()
            except Empty:
                break
            self._network_available = available
            self._internet_generation += 1
            self._internet_next_probe = 0
            if available is False and self.online_mode.requested_online:
                self._internet_status = False
                try:
                    self.online_mode.set_reachable(False)
                except OSError as exc:
                    self._set_status(f"Could not save connection mode: {exc}")
        while True:
            try:
                generation, reachable = self._internet_results.get_nowait()
            except Empty:
                break
            self._internet_probe_active = False
            if generation == self._internet_generation and self.online_mode.requested_online:
                self._internet_status = reachable
                try:
                    self.online_mode.set_reachable(reachable)
                except OSError as exc:
                    self._set_status(f"Could not save connection mode: {exc}")
        if (self.online_mode.requested_online and self._network_available is not False
                and not self._internet_probe_active):
            if self._internet_next_probe <= 0:
                generation = self._internet_generation
                self._internet_probe_active = True
                self._internet_next_probe = 10
                def probe() -> None:
                    self._internet_results.put((generation, internet_reachable()))
                Thread(target=probe, daemon=True, name="orc-internet-check").start()
            else:
                self._internet_next_probe -= 1
        self._paint_online_mode()
        self._callback_id = self._dispatcher.schedule_ui_callback(1000, self._poll_internet_status)
