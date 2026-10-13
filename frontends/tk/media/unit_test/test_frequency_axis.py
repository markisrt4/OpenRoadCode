# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Detailed axis labels stay accurate and readable on narrow displays."""
import math

import pytest

from frontends.tk.media.frequency_axis import frequency_ticks


@pytest.mark.parametrize('width', (120, 394, 614, 1000))
def test_frequency_labels_stay_in_bounds_without_overlapping(width):
    def measure(text):
        return len(text)*5
    ticks = frequency_ticks(width, measure)
    for row in (0, 1):
        bounds = sorted((x-measure(label)/2, x+measure(label)/2)
                        for _hz, label, x, lane in ticks if lane == row)
        assert all(0 <= left < right <= width for left, right in bounds)
        assert all(left >= previous_right for (_previous_left, previous_right), (left, _right)
                   in zip(bounds, bounds[1:]))
    if width >= 394:
        assert len(ticks) >= 18
        assert {250, 1000, 4000, 16000}.issubset({hz for hz, *_ in ticks})
    for hz, _label, x, _row in ticks:
        if hz not in (31.25, 16000):
            assert x == pytest.approx(width * (.04+.92*math.log(hz/31.25, 512)))


def test_wide_bands_have_frequency_center_labels_on_the_same_log_axis():
    ticks = frequency_ticks(800, lambda text: len(text)*5, band_count=8)
    hz = 31.25 * 512 ** (.5/8)
    selected = next(tick for tick in ticks if tick[0] == hz)
    assert selected[2] == pytest.approx(800 * (.04+.92*.5/8))
