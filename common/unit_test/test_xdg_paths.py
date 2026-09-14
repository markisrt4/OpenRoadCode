import os
import unittest
from pathlib import Path
from unittest.mock import patch

from common.xdg_paths import (
    openroadcode_cache_dir,
    openroadcode_config_dir,
    openroadcode_data_dir,
    openroadcode_state_dir,
    xdg_cache_home,
    xdg_config_home,
    xdg_data_home,
    xdg_state_home,
)


class XdgPathsTest(unittest.TestCase):
    def test_defaults(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "pathlib.Path.home", return_value=Path("/home/test")
        ):
            self.assertEqual(xdg_config_home(), Path("/home/test/.config"))
            self.assertEqual(xdg_data_home(), Path("/home/test/.local/share"))
            self.assertEqual(xdg_cache_home(), Path("/home/test/.cache"))
            self.assertEqual(xdg_state_home(), Path("/home/test/.local/state"))
            self.assertEqual(
                openroadcode_config_dir("radio"),
                Path("/home/test/.config/openroadcode/radio"),
            )
            self.assertEqual(
                openroadcode_data_dir("radio"),
                Path("/home/test/.local/share/openroadcode/radio"),
            )
            self.assertEqual(
                openroadcode_cache_dir("radio"),
                Path("/home/test/.cache/openroadcode/radio"),
            )
            self.assertEqual(
                openroadcode_state_dir("radio"),
                Path("/home/test/.local/state/openroadcode/radio"),
            )

    def test_absolute_overrides(self):
        with patch.dict(
            os.environ,
            {
                "XDG_CONFIG_HOME": "/mnt/config",
                "XDG_DATA_HOME": "/mnt/data",
                "XDG_CACHE_HOME": "/mnt/cache",
                "XDG_STATE_HOME": "/mnt/state",
            },
        ):
            self.assertEqual(
                openroadcode_config_dir("radio"), Path("/mnt/config/openroadcode/radio")
            )
            self.assertEqual(
                openroadcode_data_dir("radio"), Path("/mnt/data/openroadcode/radio")
            )
            self.assertEqual(
                openroadcode_cache_dir("radio"), Path("/mnt/cache/openroadcode/radio")
            )
            self.assertEqual(
                openroadcode_state_dir("radio"), Path("/mnt/state/openroadcode/radio")
            )

    def test_relative_override_is_ignored(self):
        with patch.dict(os.environ, {"XDG_DATA_HOME": "relative"}), patch(
            "pathlib.Path.home", return_value=Path("/home/test")
        ):
            self.assertEqual(xdg_data_home(), Path("/home/test/.local/share"))


if __name__ == "__main__":
    unittest.main()
