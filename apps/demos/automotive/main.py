# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run the interactive automotive UI contract demonstration."""

from apps.demos.automotive.automotive_demo_controller import (
    AutomotiveDemoController,
)
from apps.demos.automotive.automotive_demo_ui import AutomotiveDemoUi


def main() -> int:
    """Run the demo and restore the terminal on every exit path."""
    ui = AutomotiveDemoUi()
    controller = AutomotiveDemoController(ui, ui, ui, ui, ui, ui)
    if not ui.initialize():
        return 1
    controller.start()
    try:
        ui.run()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
        ui.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
