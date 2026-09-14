# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode automotive UI composition entry point."""

from __future__ import annotations

from apps.orcUi.composition.application import create_orc_ui_composition

__all__ = ["main"]


def main() -> None:
    create_orc_ui_composition().run()


if __name__ == "__main__":
    main()
