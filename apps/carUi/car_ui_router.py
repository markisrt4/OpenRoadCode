# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Application route registry for Car UI navigation destinations."""

from __future__ import annotations

from collections.abc import Callable


class CarUiRouter:
    """Route Car UI destination keys to registered screen actions."""

    def __init__(self) -> None:
        self._routes: dict[str, Callable[[], None]] = {}

    def register(
        self,
        key: str,
        action: Callable[[], None],
        *,
        replace: bool = False,
    ) -> None:
        """Register one route action.

        @param key Non-empty stable destination key.
        @param action Callback that opens the destination.
        @param replace Whether an existing route may be replaced.
        @throws ValueError If the key is empty or already registered.
        """
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("Route key must not be empty")

        if normalized_key in self._routes and not replace:
            raise ValueError(f"Route already registered: {normalized_key}")

        self._routes[normalized_key] = action

    def register_many(
        self,
        routes: dict[str, Callable[[], None]],
        *,
        replace: bool = False,
    ) -> None:
        """Register a mapping of destination keys to actions.

        @param routes Route keys and their destination callbacks.
        @param replace Whether existing routes may be replaced.
        """
        for key, action in routes.items():
            self.register(key, action, replace=replace)

    def open(self, key: str) -> None:
        """Invoke a registered destination action.

        @param key Stable destination key to open.
        @throws KeyError If no action is registered for the key.
        """
        try:
            action = self._routes[key]
        except KeyError as exc:
            available = ", ".join(sorted(self._routes)) or "<none>"
            raise KeyError(
                f"No navigation route registered for '{key}'. "
                f"Available routes: {available}"
            ) from exc

        action()

    def contains(self, key: str) -> bool:
        """Return whether a destination key is registered.

        @param key Destination key to query.
        @return True when the key is registered.
        """
        return key in self._routes

    def keys(self) -> tuple[str, ...]:
        """Return registered destination keys in insertion order.

        @return Immutable sequence of registered route keys.
        """
        return tuple(self._routes.keys())
