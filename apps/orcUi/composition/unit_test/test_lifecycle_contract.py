# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract-level tests for deferred shell lifecycle requests without Tk startup."""

import unittest
from unittest.mock import Mock

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp


class OrcUiLifecycleContractTest(unittest.TestCase):
    def make_app(self) -> OrcUiApp:
        app = object.__new__(OrcUiApp)
        app._lifecycle_handler = Mock()
        app._shutdown = Mock()
        return app

    def test_restart_records_intent_before_shell_shutdown(self) -> None:
        app = self.make_app()

        app._restart_ui()

        app._lifecycle_handler.request_restart_ui.assert_called_once_with()
        app._shutdown.assert_called_once_with()

    def test_poweroff_records_intent_before_shell_shutdown(self) -> None:
        app = self.make_app()

        app._shutdown_system()

        app._lifecycle_handler.request_poweroff.assert_called_once_with()
        app._shutdown.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
