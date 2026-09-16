# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from common.host_config import installed_target, orcui_fullscreen_default


class HostConfigTest(TestCase):
    def test_raspberry_pi_targets_default_to_fullscreen(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "host.toml"
            path.write_text('target = "rpi5"\n', encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(installed_target(path), "rpi5")
                self.assertTrue(orcui_fullscreen_default(path))

    def test_termux_defaults_to_windowed(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "host.toml"
            path.write_text('target = "termux"\n', encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertFalse(orcui_fullscreen_default(path))

    def test_termux_runtime_precedes_stale_persisted_rpi_target(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "host.toml"
            path.write_text('target = "rpi5"\n', encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "TERMUX_VERSION": "0.118",
                    "PREFIX": "/data/data/com.termux/files/usr",
                },
                clear=True,
            ):
                self.assertEqual(installed_target(path), "termux")
                self.assertFalse(orcui_fullscreen_default(path))

    def test_linux_dev_defaults_to_windowed(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "host.toml"
            path.write_text('target = "linux-dev"\n', encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertFalse(orcui_fullscreen_default(path))

    def test_environment_override_wins(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "host.toml"
            path.write_text('target = "rpi5"\n', encoding="utf-8")
            with patch.dict(os.environ, {"ORCUI_FULLSCREEN": "0"}, clear=True):
                self.assertFalse(orcui_fullscreen_default(path))

    def test_install_target_environment_precedes_file(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "host.toml"
            path.write_text('target = "linux-dev"\n', encoding="utf-8")
            with patch.dict(os.environ, {"OPENROAD_INSTALL_TARGET": "rpi4"}, clear=True):
                self.assertEqual(installed_target(path), "rpi4")
                self.assertTrue(orcui_fullscreen_default(path))

    def test_termux_runtime_precedes_install_target_environment(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "host.toml"
            path.write_text('target = "rpi5"\n', encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "TERMUX_VERSION": "0.118",
                    "PREFIX": "/data/data/com.termux/files/usr",
                    "OPENROAD_INSTALL_TARGET": "rpi5",
                },
                clear=True,
            ):
                self.assertEqual(installed_target(path), "termux")
                self.assertFalse(orcui_fullscreen_default(path))
