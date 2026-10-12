# SPDX-License-Identifier: MIT

import pytest
from ui.navigation.road_speed_limit_ui_if import RoadSpeedLimitState


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True])
def test_invalid_limit_cannot_enter_presentation(value):
    with pytest.raises(ValueError):
        RoadSpeedLimitState(value)
