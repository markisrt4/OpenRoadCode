# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Frequency labels remain readable and correspond to displayed bars."""

import pytest

from frontends.tk.media.frequency_axis import frequency_ticks


@pytest.mark.parametrize('width', (120, 394, 614, 1000))
def test_frequency_labels_stay_in_bounds_without_overlapping(width):
    measure = lambda text: len(text) * 5
    ticks = frequency_ticks(width, measure)
    bounds = sorted((x-max(5, measure(label)*.36)-2,
                     x+max(5, measure(label)*.36)+2)
                    for _hz, label, x, _row in ticks)
    assert all(0 <= left < right <= width for left, right in bounds)
    assert all(left >= previous_right for (_previous_left, previous_right), (left, _right)
               in zip(bounds, bounds[1:]))


@pytest.mark.parametrize('band_count', (8, 16, 32, 64))
def test_frequency_labels_are_centers_of_displayed_bars(band_count):
    width = 800
    ticks = frequency_ticks(width, lambda text: len(text) * 5, band_count=band_count)
    centers = {width * (.04 + .92 * (index + .5) / band_count)
               for index in range(band_count)}
    assert all(any(x == pytest.approx(center) for center in centers)
               for _hz, _label, x, _row in ticks)


def test_wider_bars_produce_fewer_frequency_labels():
    measure = lambda text: len(text) * 5
    counts = [len(frequency_ticks(800, measure, band_count=count))
              for count in (8, 16, 32, 64)]

    assert counts == sorted(counts)
    assert counts[0] == 8
    assert counts[-1] < 64
