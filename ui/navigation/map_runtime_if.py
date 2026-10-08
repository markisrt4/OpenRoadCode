# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native map host lifecycle contract independent of process implementation."""
from typing import Protocol
from ui.theme import ThemeMode


class MapRuntimeIf(Protocol):
    """Control a native map presentation without importing backend infrastructure."""

    def set_theme(self, mode: ThemeMode) -> None:
        """Select map appearance.

        @param mode Requested theme mode.
        """
        ...

    def launch(self, parent_window_id: int) -> None:
        """Attach map presentation to a native host.

        @param parent_window_id Native parent window identifier supplied by the frontend.
        """
        ...

    def stop(self) -> None:
        """Stop the current native map presentation."""
        ...
