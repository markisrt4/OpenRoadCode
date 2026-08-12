# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for Car UI position-source selection."""

import os
import unittest
from unittest.mock import patch

from apps.carUi.runtime.position_source_factory import create_position_source


class PositionSourceFactoryTest(unittest.TestCase):
    @patch("apps.carUi.runtime.position_source_factory.PersistentPositionSource")
    @patch("apps.carUi.runtime.position_source_factory.GpsdPositionSource")
    def test_gpsd_is_default(self, gpsd_source, persistent_source) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = create_position_source()

        self.assertIs(result, persistent_source.return_value)
        self.assertIs(
            persistent_source.call_args.args[0],
            gpsd_source.return_value,
        )

    @patch("apps.carUi.runtime.position_source_factory.PersistentPositionSource")
    @patch("apps.carUi.runtime.position_source_factory.BrowserPositionSource")
    def test_browser_uses_configured_address(
        self,
        browser_source,
        persistent_source,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "CARUI_BROWSER_POSITION_HOST": "0.0.0.0",
                "CARUI_BROWSER_POSITION_PORT": "9000",
            },
        ):
            result = create_position_source("browser")

        self.assertIs(result, persistent_source.return_value)
        browser_source.assert_called_once_with(host="0.0.0.0", port=9000)

    @patch("apps.carUi.runtime.position_source_factory.GpsdPositionSource")
    def test_cache_can_be_disabled(self, gpsd_source) -> None:
        with patch.dict(
            os.environ,
            {"CARUI_POSITION_CACHE": "0"},
            clear=True,
        ):
            result = create_position_source()

        self.assertIs(result, gpsd_source.return_value)

    def test_rejects_unknown_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown"):
            create_position_source("unknown")


if __name__ == "__main__":
    unittest.main()
