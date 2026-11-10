# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Own transient map-controls drawer visibility."""

from ui.navigation.map_controls_drawer_ui import (
    MapControlsDrawerRequestHandlerIf,
    MapControlsDrawerState,
    MapControlsDrawerUiIf,
)


class MapControlsDrawerController(MapControlsDrawerRequestHandlerIf):
    def __init__(self) -> None:
        self._state = MapControlsDrawerState()
        self._ui: MapControlsDrawerUiIf | None = None

    def set_ui(self, ui: MapControlsDrawerUiIf | None) -> None:
        self._ui = ui
        if ui is not None:
            ui.set_map_controls_drawer_state(self._state)

    def request_map_controls_expanded(self, expanded: bool) -> None:
        state = MapControlsDrawerState(bool(expanded))
        if state == self._state:
            return
        self._state = state
        if self._ui is not None:
            self._ui.set_map_controls_drawer_state(state)
