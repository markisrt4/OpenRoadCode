# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Module entry point for ``python -m apps.orcUi``."""

from __future__ import annotations

from importlib import import_module
import os
import shlex
import sys
import time


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
        "    ./runOrcUi",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _require_musicforge() -> None:
    """Check the required analysis API before application composition imports."""
    try:
        analysis = import_module("musicforge.analysis")
        for name in ("MusicAnalyzer", "MusicAnalyzerIf", "MusicAnalysisState", "PercussionActivity"):
            getattr(analysis, name)
    except (ImportError, AttributeError, OSError) as error:
        interpreter = shlex.quote(sys.executable)
        print(
            "OpenRoadCode UI cannot start: libMusicForge audio analysis is unavailable.\n"
            f"Python: {sys.executable}\n"
            f"Import problem: {error}\n\n"
            "Install or repair it in this Python environment from the repository root:\n"
            f"    PYTHON={interpreter} bash scripts/installers/install_libmusicforge.sh\n\n"
            "Then run ./runOrcUi again.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None


def _main() -> None:
    _require_display()
    if not any(option in sys.argv[1:] for option in ("-h", "--help", "--check-ecu-gl")):
        _require_musicforge()
    startup_started_at = time.monotonic()
    print(
        "[    0.000] Startup initiated",
        file=sys.stderr,
        flush=True,
    )
    from apps.orcUi.main import main

    main(startup_started_at=startup_started_at)


if __name__ == "__main__":
    _main()
