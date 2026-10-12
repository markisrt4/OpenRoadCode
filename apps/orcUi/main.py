# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode automotive UI composition entry point."""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from collections.abc import Callable
from typing import TextIO
from common.logging.structured import configure_logging, event
from common.logging.viewer import follow

__all__ = ["main"]


class StartupReporter:
    """Render immediate terminal milestones and retain their structured timings."""

    _LEADER_COLUMN = 64

    def __init__(
        self,
        logger: logging.Logger,
        *,
        started_at: float,
        output: TextIO | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._logger = logger
        self._started_at = started_at
        self._previous_at = started_at
        self._output = output or sys.stderr
        self._clock = clock

    def __call__(self, stage: str, message: str) -> None:
        now = self._clock()
        duration = max(0.0, now - self._previous_at)
        elapsed = max(0.0, now - self._started_at)
        self._previous_at = now
        label = f"[{elapsed:9.3f}] {message} "
        leader = "." * max(3, self._LEADER_COLUMN - len(label))
        suffix = f"(+{duration:.3f}s)"
        print(f"{label}{leader} {suffix}", file=self._output, flush=True)
        event(
            self._logger,
            logging.INFO,
            "app.startup.progress",
            message,
            stage=stage,
            duration_ms=round(duration * 1000),
            elapsed_ms=round(elapsed * 1000),
        )


def main(*, startup_started_at: float | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--follow-logs", action="store_true")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--log-component", help="Live viewer component prefix")
    parser.add_argument("--check-ecu-gl", action="store_true",
                        help="Check the ECU OpenGL renderer and exit")
    args = parser.parse_args()
    if args.check_ecu_gl:
        from apps.orcUi.frontend.tk.ecu_gl_diagnostics import main as check_ecu_gl

        raise SystemExit(check_ecu_gl())
    if args.log_level:
        import os

        os.environ["ORC_LOG_LEVEL"] = args.log_level
    store = configure_logging(level=args.log_level, stderr=False)
    logger = logging.getLogger("orc.lifecycle")
    report_startup = StartupReporter(
        logger,
        started_at=startup_started_at or time.monotonic(),
    )
    report_startup("application_modules", "Application modules loaded")

    stop = threading.Event()
    viewer = None
    if args.follow_logs:
        snapshot = store.path.stat() if store.path.exists() else None
        start_offset = (snapshot.st_ino, snapshot.st_size) if snapshot else None
        viewer = threading.Thread(
            target=follow,
            kwargs={
                "path": store.path,
                "stop": stop,
                "component": args.log_component,
                "level": args.log_level or "INFO",
                "start_offset": start_offset,
            },
            daemon=True,
        )
        viewer.start()
    event(logger, logging.INFO, "app.started", "ORC UI starting")
    try:
        from apps.orcUi.composition.application import create_orc_ui_composition

        report_startup("composition_import", "Subsystem composition loaded")
        create_orc_ui_composition(progress=report_startup).run()
    except Exception:
        logger.exception("ORC UI failed", extra={"event": "app.failed"})
        raise
    finally:
        event(logger, logging.INFO, "app.stopped", "ORC UI stopped")
        stop.set()
        if viewer:
            viewer.join(timeout=2)


if __name__ == "__main__":
    main()
