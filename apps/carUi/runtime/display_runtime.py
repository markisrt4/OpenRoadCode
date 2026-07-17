from __future__ import annotations

import os


def configure_display() -> str:
    """Use the inherited X11-forwarding display or an explicit override."""

    display = _clean_display(os.getenv("DISPLAY"))
    if display is not None:
        return display

    display = _clean_display(os.getenv("CARUI_DISPLAY"))
    if display is None:
        raise RuntimeError(
            "No X11 display is available. Connect with ssh -X or ssh -Y "
            "and verify that $DISPLAY is set before launching CarUI."
        )

    os.environ["DISPLAY"] = display
    print(f"[CarUI] Using explicit X display {display}")
    return display


def _clean_display(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None
