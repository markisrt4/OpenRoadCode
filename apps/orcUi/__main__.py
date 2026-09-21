# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Module entry point for ``python -m apps.orcUi``."""

from __future__ import annotations

import os
import sys


def _require_display() -> None:
    """Exit with a useful message when no graphical X11 display is configured."""

    if os.environ.get("DISPLAY"):
        return

    print(
        "OpenRoadCode UI cannot start: DISPLAY is not set.\n\n"
        "A graphical X11 display is required.\n\n"
        "Termux:X11 normally uses:\n"
        "    export DISPLAY=:1\n\n"
        "Then run:\n"
        "    python -m apps.orcUi",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _main() -> None:
    _require_display()
    from apps.orcUi.main import main

    main()


if __name__ == "__main__":
    _main()
