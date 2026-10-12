# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Provider turn codes become stable visual hints without parsing road text."""

import pytest
from controllers.route_planning.valhalla_route_planning_controller import ValhallaRoutePlanningController
from ui.navigation.route_types import RouteTurn


@pytest.mark.parametrize("code,turn", [
    (15, RouteTurn.LEFT), (10, RouteTurn.RIGHT), (8, RouteTurn.STRAIGHT),
    (13, RouteTurn.U_TURN), (26, RouteTurn.ROUNDABOUT), (4, RouteTurn.ARRIVE),
    (None, RouteTurn.UNKNOWN), (999, RouteTurn.UNKNOWN), (True, RouteTurn.UNKNOWN),
])
def test_typed_direction_is_provider_data_not_instruction_guessing(code, turn):
    result = ValhallaRoutePlanningController._parse_maneuver({
        "type": code, "instruction": "Continue onto Left Street",
        "street_names": ["", "Left Street"],
    })
    assert result.turn == turn
    assert result.road_name == "Left Street"
