# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode automotive UI entry point."""

from apps.orcUi.orc_ui_app import (
    BLUE,
    BORDER,
    GREEN,
    MUTED,
    PANEL,
    PURPLE,
    RED,
    TEXT,
    TOP_BG,
    YELLOW,
    OrcUiApp,
)

__all__ = ["OrcUiApp", "main"]


def main() -> None:
    """Run the integrated OpenRoadCode UI."""
    OrcUiApp().run()


if __name__ == "__main__":
    main()
