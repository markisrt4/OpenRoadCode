# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Concrete no-op map UI implementation."""

from ui.navigation.map_request_handler_if import MapRequestHandlerIf
from ui.navigation.map_ui_if import MapState, MapUiIf


class MapUiStub(MapUiIf):
    """Ignore map state and callback registration."""

    def set_map_state(self, state: MapState | None) -> None:
        pass

    def set_map_request_handler(
        self,
        handler: MapRequestHandlerIf | None,
    ) -> None:
        pass
