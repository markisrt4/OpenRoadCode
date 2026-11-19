# SPDX-License-Identifier: MIT
"""Hardware-free SDRForge radio sidebar geometry checks."""

import pytest

from apps.orcUi.frontend.tk.radio_panel import receiver_sidebar_width


@pytest.mark.parametrize(("panel_width", "expected"), [
    (1280, 320),
    (1024, 256),
    (960, 240),
    (800, 240),
    (1600, 320),
])
def test_sidebar_reserves_spectrum_space(panel_width: int, expected: int) -> None:
    assert receiver_sidebar_width(panel_width) == expected
