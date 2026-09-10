# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode automotive UI entry point."""

from __future__ import annotations

from apps.orcUi.composition.application import create_orc_ui_composition
from apps.orcUi.orc_ui_app import OrcUiApp

__all__ = ["OrcUiApp", "main"]


def main() -> None:
    create_orc_ui_composition().run()


if __name__ == "__main__":
    main()
