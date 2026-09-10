# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility alias for the integrated ORC shell."""

from apps.orcUi.orc_ui_app import OrcUiApp


class ComposedHomeShell(OrcUiApp):
    """Backward-compatible name for the shell with composition-owned Home slots."""
