# SPDX-License-Identifier: MIT
"""Shared code-native spectrum artwork for inactive music surfaces."""

import tkinter as tk


def paint_spectrum_illustration(
    canvas: tk.Canvas,
    width: int,
    height: int,
    *,
    muted_fraction: float = 0.48,
) -> None:
    """Paint the Media spectrum motif without implying live analyzer data."""
    if width < 2 or height < 2:
        return
    base = tuple(value // 256 for value in canvas.winfo_rgb(canvas.cget("bg")))

    def mix(left: tuple[int, ...], right: tuple[int, ...], amount: float) -> str:
        return "#" + "".join(
            f"{round(a + (b - a) * amount):02x}" for a, b in zip(left, right)
        )

    palette = ((35, 210, 186), (66, 145, 245), (165, 104, 238))
    profile = (0.24, 0.40, 0.32, 0.62, 0.85, 0.56, 0.96, 0.72,
               0.48, 0.68, 0.38, 0.54)
    count = 36
    step = width / count
    for index in range(count):
        position = index / (count - 1) * 2
        segment = min(1, int(position))
        color = mix(palette[segment], palette[segment + 1], position - segment)
        rgb = tuple(int(color[offset:offset + 2], 16) for offset in (1, 3, 5))
        x = index * step
        canvas.create_rectangle(
            x, 0, x + step + 1, height,
            fill=mix(base, rgb, 0.10), outline="",
        )
        bar_height = height * 0.72 * profile[index % len(profile)]
        strength = 0.22 if index < count * muted_fraction else 0.85
        canvas.create_rectangle(
            x + step * 0.2, (height - bar_height) / 2,
            x + step * 0.8, (height + bar_height) / 2,
            fill=mix(base, rgb, strength), outline="",
        )
