# SPDX-License-Identifier: MIT
"""Start the optional splash without moving ORC's Tk work off its main thread."""

from __future__ import annotations

import subprocess
import sys
from threading import Thread


class StartupSplashProcess:
    def __init__(self, process: subprocess.Popen[str]) -> None:
        self._process = process

    @classmethod
    def start(cls) -> StartupSplashProcess | None:
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "frontends.tk.system.orc_startup_splash"],
                stdin=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as error:
            print(f"Could not start the ORC splash: {error}", file=sys.stderr)
            return None
        Thread(target=process.wait, name="orc-splash-reaper", daemon=True).start()
        return cls(process)

    def finish(self, failure: str | None = None) -> None:
        """Close the splash, or leave a short-lived failure message visible."""
        pipe = self._process.stdin
        if pipe is None or pipe.closed:
            return
        try:
            with pipe:
                if failure:
                    pipe.write(failure[:750].replace("\n", " ") + "\n")
        except OSError:
            # The splash may already have closed or been unavailable.
            pass
