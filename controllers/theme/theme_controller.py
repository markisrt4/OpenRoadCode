# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own the selected application theme without knowing how frontends render it."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from ui.theme import ThemeMode, UiTheme

ThemeListener = Callable[[ThemeMode, UiTheme], None]


class ThemeController:
    """Manage theme selection and notify presentation listeners."""

    def __init__(
        self,
        themes: Mapping[ThemeMode, UiTheme],
        initial_mode: ThemeMode = ThemeMode.DARK,
    ) -> None:
        self._themes = dict(themes)
        if initial_mode not in self._themes:
            raise ValueError(f"No theme configured for mode {initial_mode.value}")
        self._mode = initial_mode
        self._listeners: list[ThemeListener] = []

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    @property
    def theme(self) -> UiTheme:
        return self._themes[self._mode]

    def set_mode(self, mode: ThemeMode) -> None:
        if mode not in self._themes:
            raise ValueError(f"No theme configured for mode {mode.value}")
        if mode is self._mode:
            return
        self._mode = mode
        self._notify()

    def toggle(self) -> ThemeMode:
        next_mode = ThemeMode.LIGHT if self._mode is ThemeMode.DARK else ThemeMode.DARK
        self.set_mode(next_mode)
        return self._mode

    def subscribe(self, listener: ThemeListener, *, notify: bool = True) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)
        if notify:
            listener(self._mode, self.theme)

    def unsubscribe(self, listener: ThemeListener) -> None:
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener(self._mode, self.theme)
