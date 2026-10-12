# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from controllers.navigation.map_controls_drawer_controller import MapControlsDrawerController
from ui.navigation import MapControlsDrawerState, MapControlsDrawerUiIf


def test_drawer_publishes_initial_and_requested_state() -> None:
    ui = Mock(spec=MapControlsDrawerUiIf)
    controller = MapControlsDrawerController()

    controller.set_ui(ui)
    controller.request_map_controls_expanded(True)

    assert ui.set_map_controls_drawer_state.call_args_list[0].args == (
        MapControlsDrawerState(False),
    )
    assert ui.set_map_controls_drawer_state.call_args_list[1].args == (
        MapControlsDrawerState(True),
    )


def test_drawer_does_not_publish_after_ui_disconnect() -> None:
    ui = Mock(spec=MapControlsDrawerUiIf)
    controller = MapControlsDrawerController()
    controller.set_ui(ui)
    controller.set_ui(None)

    controller.request_map_controls_expanded(True)

    assert ui.set_map_controls_drawer_state.call_count == 1
