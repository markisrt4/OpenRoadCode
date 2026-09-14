# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk text rendering for toolkit-independent semantic icons."""

from ui.icon import IconId


_ICON_TEXT: dict[IconId, str] = {
    IconId.POWER: "⏻",
    IconId.MICROPHONE: "🎙",
    IconId.CAMERA: "▣",
    IconId.DISPLAY: "▣",
    IconId.BRIGHTNESS: "☀",
    IconId.VOLUME: "🔊",
    IconId.VOLUME_MUTED: "🔇",
}


def icon_text(icon: IconId) -> str:
    """Return the Tk text glyph for a semantic icon.

    Frontends are intentionally free to render the same IconId using SVG,
    CSS, native assets, Unicode, or another presentation mechanism.
    """
    return _ICON_TEXT.get(icon, "")


__all__ = ["icon_text"]
