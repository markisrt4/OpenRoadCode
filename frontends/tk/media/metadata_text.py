# SPDX-License-Identifier: MIT
"""Fit card metadata to measured text space without clipping characters."""

from collections.abc import Callable


def fit_metadata_text(text: str, width: int, measure: Callable[[str], int], *, lines: int) -> str:
    remaining = " ".join(text.split())
    result: list[str] = []
    for index in range(max(0, lines)):
        if not remaining:
            break
        if measure(remaining) <= width:
            result.append(remaining)
            break
        suffix = "…" if index == lines - 1 else ""
        if measure(suffix) > width:
            return "\n".join(result)
        low, high = 0, len(remaining)
        while low < high:
            middle = (low + high + 1) // 2
            if measure(remaining[:middle].rstrip() + suffix) <= width:
                low = middle
            else:
                high = middle - 1
        cut = low
        if not suffix and " " in remaining[:cut]:
            cut = remaining.rfind(" ", 0, cut + 1)
        if not cut and not suffix:
            break
        result.append(remaining[:cut].rstrip() + suffix)
        remaining = remaining[cut:].lstrip()
    return "\n".join(result)
