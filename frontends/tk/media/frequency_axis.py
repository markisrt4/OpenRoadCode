# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Responsive frequency labels aligned with analyzer bar centers."""


def frequency_ticks(width, measure, band_count=64):
    """Fit angled labels selected only from the displayed logarithmic bars."""
    if band_count <= 0:
        return ()
    result = []
    right_edge = -1.0
    for index in range(band_count):
        hz = 31.25 * 512 ** ((index + .5) / band_count)
        label = f'{hz / 1000:.3g}k' if hz >= 1000 else f'{hz:.3g}'
        x = width * (.04 + .92 * (index + .5) / band_count)
        # A 45-degree label occupies roughly 70% of its unrotated width.
        half = max(5.0, measure(label) * .36)
        left, right = x - half - 2, x + half + 2
        if left >= right_edge and left >= 0 and right <= width:
            result.append((hz, label, x, 0))
            right_edge = right
    return tuple(result)
