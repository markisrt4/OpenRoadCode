# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract-level tests for shell system-volume behavior without Tk startup."""

import unittest
from unittest.mock import Mock

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp


class OrcUiVolumeContractTest(unittest.TestCase):
    def make_app(self) -> OrcUiApp:
        app = object.__new__(OrcUiApp)
        app._volume_percent = None
        app._volume_muted = None
        app._volume_request_handler = None
        return app

    def test_volume_requests_are_forwarded_semantically(self) -> None:
        app = self.make_app()
        handler = Mock()
        app.set_volume_request_handler(handler)

        app._request_volume_down()
        app._request_volume_up()

        handler.request_volume_down.assert_called_once_with()
        handler.request_volume_up.assert_called_once_with()

    def test_missing_volume_handler_is_a_safe_noop(self) -> None:
        app = self.make_app()

        app._request_volume_down()
        app._request_volume_up()

    def test_volume_text_reflects_unavailable_muted_and_percentage_states(self) -> None:
        app = self.make_app()
        self.assertEqual("🔊 --", app._volume_text())

        app._volume_percent = 42.4
        self.assertEqual("🔊 42%", app._volume_text())

        app._volume_muted = True
        self.assertEqual("🔇 42%", app._volume_text())


if __name__ == "__main__":
    unittest.main()
