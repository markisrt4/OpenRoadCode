# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Geometry tests for ECU dashboard visuals."""

import pytest

from apps.orcUi.frontend.tk.ecu_panel import bounded_marker_x


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-100.0, 17.0),
        (-20.0, 17.0),
        (0.0, 100.0),
        (20.0, 183.0),
        (100.0, 183.0),
    ],
)
def test_bounded_marker_x_keeps_marker_inside_rail(value: float, expected: float) -> None:
    assert bounded_marker_x(
        value,
        minimum=-20.0,
        maximum=20.0,
        rail_start=10.0,
        rail_end=190.0,
        radius=7.0,
    ) == pytest.approx(expected)
