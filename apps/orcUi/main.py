# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode automotive UI composition entry point."""

from __future__ import annotations

import argparse
import logging
import threading
from common.logging.structured import configure_logging, event
from common.logging.viewer import follow
from apps.orcUi.composition.application import create_orc_ui_composition

__all__ = ["main"]


def main() -> None:
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
        create_orc_ui_composition().run()
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
