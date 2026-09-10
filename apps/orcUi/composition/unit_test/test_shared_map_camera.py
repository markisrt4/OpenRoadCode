# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the composition-owned map camera reference."""

import unittest
from unittest.mock import Mock

from apps.orcUi.shared_map_camera import (
    clear_shared_map_camera_runtime,
    get_shared_map_camera_runtime,
    install_shared_map_camera_runtime,
)


class SharedMapCameraTest(unittest.TestCase):
    def tearDown(self) -> None:
        try:
            runtime = get_shared_map_camera_runtime()
        except RuntimeError:
            return
        clear_shared_map_camera_runtime(runtime)

    def test_runtime_must_be_installed_by_composition(self) -> None:
        with self.assertRaises(RuntimeError):
            get_shared_map_camera_runtime()

    def test_installed_runtime_is_returned_and_can_be_cleared(self) -> None:
        runtime = Mock()

        install_shared_map_camera_runtime(runtime)
        self.assertIs(get_shared_map_camera_runtime(), runtime)

        clear_shared_map_camera_runtime(runtime)
        with self.assertRaises(RuntimeError):
            get_shared_map_camera_runtime()

    def test_different_runtime_cannot_replace_installed_owner(self) -> None:
        first = Mock()
        second = Mock()
        install_shared_map_camera_runtime(first)

        with self.assertRaises(RuntimeError):
            install_shared_map_camera_runtime(second)

        self.assertIs(get_shared_map_camera_runtime(), first)


if __name__ == "__main__":
    unittest.main()
