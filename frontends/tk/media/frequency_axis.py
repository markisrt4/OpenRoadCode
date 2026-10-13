# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Responsive frequency labels on the analyzer's fixed logarithmic axis."""
import math


MAJOR_HZ = (31.25, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)
MINOR_HZ = (40, 50, 80, 100, 160, 200, 315, 400, 630, 800,
            1250, 1600, 2500, 3150, 5000, 6300, 10000, 12500)


def frequency_ticks(width, measure, band_count=64):
    """Prioritize octave labels, then fit third-octave labels in two clear rows."""
    occupied = [[], []]
    result = []
    centers = tuple(31.25 * 512 ** ((i+.5)/band_count) for i in range(band_count)) if band_count < 32 else MINOR_HZ
    for hz in (*MAJOR_HZ, *centers):
        label = f'{hz / 1000:.3g}k' if hz >= 1000 else f'{hz:.3g}'
        if hz == 31.25:
            label = '31.25'
        half = measure(label) / 2
        if half * 2 + 4 > width:
            continue
        x = width * (.04 + .92 * math.log(hz / 31.25, 512))
        x = max(half + 2, min(width - half - 2, x))
        for row in ((0, 1) if hz in MAJOR_HZ else (1, 0)):
            interval = (x - half - 2, x + half + 2)
            if all(interval[1] <= left or interval[0] >= right for left, right in occupied[row]):
                occupied[row].append(interval)
                result.append((hz, label, x, row))
                break
    return tuple(sorted(result))
