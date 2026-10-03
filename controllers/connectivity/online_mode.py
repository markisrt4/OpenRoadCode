# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""User-selected permission for ORC features that require internet access."""
from collections.abc import Callable
import json
from pathlib import Path

from common.xdg_paths import openroadcode_config_dir


class OnlineModeController:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or openroadcode_config_dir('online-mode.json')
        self._online = True
        self._listeners: list[Callable[[bool], None]] = []
        try:
            value = json.loads(self._path.read_text()).get('online')
            if isinstance(value, bool):
                self._online = value
        except (OSError, ValueError, AttributeError):
            pass

    @property
    def online(self) -> bool:
        return self._online

    def set_online(self, online: bool) -> None:
        online = bool(online)
        if online == self._online:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        staged = self._path.with_suffix('.tmp')
        staged.write_text(json.dumps({'online': online}))
        staged.replace(self._path)
        self._online = online
        for listener in tuple(self._listeners):
            listener(online)

    def subscribe(self, listener: Callable[[bool], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)
        return unsubscribe


def saved_online_mode(path: Path | None = None) -> bool:
    """Read the shared preference for services running outside the UI process."""
    return OnlineModeController(path).online
