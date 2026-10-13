# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""GL color values resolved from the supplied semantic ORC theme."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenePalette:
    """Normalized render colors; defaults preserve standalone dark scene calls."""

    background: tuple = (.015, .025, .055)
    grid: tuple = (.12, .18, .22)
    guides: tuple = (.18, .3, .38)
    text: tuple = (.88, .96, 1)


def scene_palette(ui, resolve):
    """Use Tk's color resolver for hex and named semantic colors alike."""
    def rgb(color):
        return tuple(channel/65535 for channel in resolve(color))
    return ScenePalette(rgb(ui.background), rgb(ui.border), rgb(ui.text_muted), rgb(ui.text))
