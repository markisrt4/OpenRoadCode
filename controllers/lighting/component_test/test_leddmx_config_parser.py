from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from controllers.lighting.parsers.leddmx_config_parser import (
    load_leddmx_config,
)


_CONFIG = """
[bluetooth]
address = "AA:BB:CC:DD:EE:FF"
service_uuid = "0000ffe0-0000-1000-8000-00805f9b34fb"
characteristic_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"
"""


class LedDmxConfigParserTest(unittest.TestCase):
    def test_optional_address_is_loaded(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "leddmx.toml"
            path.write_text(_CONFIG, encoding="utf-8")

            config = load_leddmx_config(path)

        self.assertEqual("AA:BB:CC:DD:EE:FF", config.address)

    def test_address_defaults_to_none(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "leddmx.toml"
            path.write_text(
                _CONFIG.replace(
                    'address = "AA:BB:CC:DD:EE:FF"\n',
                    "",
                ),
                encoding="utf-8",
            )

            config = load_leddmx_config(path)

        self.assertIsNone(config.address)


if __name__ == "__main__":
    unittest.main()
