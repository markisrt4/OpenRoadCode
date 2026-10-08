# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Combine the user's internet preference with observed reachability."""
from collections.abc import Callable
import json
from pathlib import Path

from common.xdg_paths import openroadcode_config_dir


class OnlineModeController:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or openroadcode_config_dir('online-mode.json')
        self._requested_online = True
        self._reachable: bool | None = None
        self._listeners: list[Callable[[bool], None]] = []
        try:
            document = json.loads(self._path.read_text())
            requested = document.get('requested_online', document.get('online'))
            if isinstance(requested, bool):
                self._requested_online = requested
            if self._requested_online and document.get('online') is False:
                self._reachable = False
        except (OSError, ValueError, AttributeError):
            pass

    @property
    def online(self) -> bool:
        return self._requested_online and self._reachable is not False

    @property
    def requested_online(self) -> bool:
        """Allow recovery probes unless the user explicitly chose offline."""
        return self._requested_online

    def set_online(self, online: bool) -> None:
        self._update(bool(online), self._reachable)

    def set_reachable(self, reachable: bool | None) -> None:
        self._update(self._requested_online, reachable)

    def _update(self, requested: bool, reachable: bool | None) -> None:
        previous = self.online
        if requested == self._requested_online and reachable == self._reachable:
            return
        online = requested and reachable is not False
        self._path.parent.mkdir(parents=True, exist_ok=True)
        staged = self._path.with_suffix('.tmp')
        staged.write_text(json.dumps({'online': online, 'requested_online': requested}))
        staged.replace(self._path)
        self._requested_online = requested
        self._reachable = reachable
        if online != previous:
            for listener in tuple(self._listeners):
                listener(online)

    def subscribe(self, listener: Callable[[bool], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)
        return unsubscribe


def saved_online_mode(path: Path | None = None) -> bool:
    """Read effective mode for services running outside the UI process."""
    return OnlineModeController(path).online
