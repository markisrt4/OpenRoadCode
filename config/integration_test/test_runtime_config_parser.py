# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from config.component_test.runtime_config_test_app import main
from config.runtime_config import RuntimeConfigParser


VALID_TOML = """
[runtime]
remote_display = ":2"

[rigctl]
host = "127.0.0.1"
port = 4532

[environmental.barometric_sensor]
driver = "bmp388"
address = 0x77

[input.rotary_encoders]
volume_index = 0

[[input.rotary_encoders.devices]]
driver = "seesaw"
address = 0x36

[[input.rotary_encoders.devices]]
driver = "seesaw"
address = 0x37

[[input.rotary_encoders.devices]]
driver = "seesaw"
address = 0x38

[[radios]]
key = "fm_radio"
config = "fm_radio.json"
backend = "rigctl"
launcher = "sdrpp"
enabled = true
"""


class RuntimeConfigTestAppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project_root = Path(self.temp_dir.name)
        self.radio_dir = self.project_root / "config" / "radio"
        self.radio_dir.mkdir(parents=True)
        (self.radio_dir / "fm_radio.json").write_text("{}", encoding="utf-8")
        self.config_path = self.project_root / "runtime.toml"
        self.config_path.write_text(VALID_TOML, encoding="utf-8")

    def test_valid_config_returns_zero(self) -> None:
        result = main([str(self.config_path), "--project-root", str(self.project_root), "--quiet"])
        self.assertEqual(0, result)

    def test_image_cache_config_is_parsed(self) -> None:
        from config.component_test.runtime_config_test_app import validate_config
        self.config_path.write_text(
            VALID_TOML + '\n[image_cache]\ndirectory = "var/artwork"\nmax_entries = 12\n',
            encoding="utf-8",
        )
        config = validate_config(self.config_path, project_root=self.project_root)
        self.assertEqual((self.project_root / "var" / "artwork").resolve(), config.image_cache.directory)
        self.assertEqual(12, config.image_cache.max_entries)

    def test_audio_output_config_is_parsed(self) -> None:
        from config.component_test.runtime_config_test_app import validate_config
        self.config_path.write_text(
            VALID_TOML + '\n[audio]\noutput = "usb"\ndevice_match = "C-Media"\n',
            encoding="utf-8",
        )
        config = validate_config(self.config_path, project_root=self.project_root)
        self.assertEqual("usb", config.audio.output)
        self.assertEqual("C-Media", config.audio.device_match)

    def test_media_display_is_parsed_independently(self) -> None:
        self.config_path.write_text(
            VALID_TOML.replace('remote_display = ":2"', 'remote_display = ":2"\nmedia_display = ":0"'),
            encoding="utf-8",
        )
        config = RuntimeConfigParser(self.config_path, project_root=self.project_root).load()
        self.assertEqual(":2", config.runtime.remote_display)
        self.assertEqual(":0", config.runtime.media_display)

    def test_auxiliary_display_defaults_to_local_desktop(self) -> None:
        config = RuntimeConfigParser(self.config_path, project_root=self.project_root).load()
        self.assertEqual(":0", config.runtime.auxiliary_display)

    def test_auxiliary_display_is_configurable(self) -> None:
        self.config_path.write_text(
            VALID_TOML.replace('remote_display = ":2"', 'remote_display = ":2"\nauxiliary_display = ":4"'),
            encoding="utf-8",
        )
        config = RuntimeConfigParser(self.config_path, project_root=self.project_root).load()
        self.assertEqual(":4", config.runtime.auxiliary_display)

    def test_position_cache_defaults_are_loaded(self) -> None:
        config = RuntimeConfigParser(self.config_path, project_root=self.project_root).load()
        self.assertTrue(config.position_cache.enabled)
        self.assertEqual(604800.0, config.position_cache.max_age_seconds)

    def test_position_cache_configuration_is_parsed(self) -> None:
        self.config_path.write_text(
            VALID_TOML + "\n[position_cache]\n" + "enabled = false\n" + 'directory = "var/position"\n' + "max_age_seconds = 3600\n",
            encoding="utf-8",
        )
        config = RuntimeConfigParser(self.config_path, project_root=self.project_root).load()
        self.assertFalse(config.position_cache.enabled)
        self.assertEqual((self.project_root / "var" / "position").resolve(), config.position_cache.directory)
        self.assertEqual(3600.0, config.position_cache.max_age_seconds)

    def test_rotary_encoder_config_is_parsed(self) -> None:
        from config.component_test.runtime_config_test_app import validate_config
        config = validate_config(self.config_path, project_root=self.project_root)
        self.assertEqual((0x36, 0x37, 0x38), tuple(device.address for device in config.input.rotary_encoders.devices))
        self.assertEqual(0, config.input.rotary_encoders.volume_index)

    def test_barometric_sensor_config_is_parsed(self) -> None:
        from config.component_test.runtime_config_test_app import validate_config
        config = validate_config(self.config_path, project_root=self.project_root)
        sensor = config.environmental.barometric_sensor
        self.assertEqual("bmp388", sensor.driver)
        self.assertEqual(0x77, sensor.address)

    def test_bmp390_and_alternate_address_are_supported(self) -> None:
        from config.component_test.runtime_config_test_app import validate_config
        self.config_path.write_text(
            VALID_TOML.replace('driver = "bmp388"\naddress = 0x77', 'driver = "bmp390"\naddress = 0x76'),
            encoding="utf-8",
        )
        config = validate_config(self.config_path, project_root=self.project_root)
        sensor = config.environmental.barometric_sensor
        self.assertEqual("bmp390", sensor.driver)
        self.assertEqual(0x76, sensor.address)

    def test_invalid_barometric_sensor_driver_is_rejected(self) -> None:
        self.config_path.write_text(VALID_TOML.replace('driver = "bmp388"', 'driver = "bmp280"'), encoding="utf-8")
        result = main([str(self.config_path), "--project-root", str(self.project_root), "--quiet"])
        self.assertEqual(1, result)

    def test_invalid_barometric_sensor_address_is_rejected(self) -> None:
        self.config_path.write_text(VALID_TOML.replace("address = 0x77", "address = 0x80"), encoding="utf-8")
        result = main([str(self.config_path), "--project-root", str(self.project_root), "--quiet"])
        self.assertEqual(1, result)

    def test_mixed_seesaw_and_gpio_encoders_are_parsed(self) -> None:
        from config.runtime_config import GpioEncoderConfig, SeesawEncoderConfig
        from config.component_test.runtime_config_test_app import validate_config
        mixed_toml = VALID_TOML.replace(
            '''[[input.rotary_encoders.devices]]
driver = "seesaw"
address = 0x38''',
            '''[[input.rotary_encoders.devices]]
driver = "gpio"
pin_a = 11
pin_b = 13
button = 15''',
        )
        self.config_path.write_text(mixed_toml, encoding="utf-8")
        config = validate_config(self.config_path, project_root=self.project_root)
        self.assertIsInstance(config.input.rotary_encoders.devices[0], SeesawEncoderConfig)
        gpio = config.input.rotary_encoders.devices[2]
        self.assertIsInstance(gpio, GpioEncoderConfig)
        self.assertEqual((11, 13, 15), (gpio.pin_a, gpio.pin_b, gpio.button))

    def test_volume_encoder_index_must_identify_a_device(self) -> None:
        self.config_path.write_text(VALID_TOML.replace("volume_index = 0", "volume_index = 3"), encoding="utf-8")
        result = main([str(self.config_path), "--project-root", str(self.project_root), "--quiet"])
        self.assertEqual(1, result)

    def test_seesaw_encoder_addresses_must_be_unique(self) -> None:
        self.config_path.write_text(VALID_TOML.replace("address = 0x38", "address = 0x37"), encoding="utf-8")
        result = main([str(self.config_path), "--project-root", str(self.project_root), "--quiet"])
        self.assertEqual(1, result)

    def test_invalid_config_returns_one(self) -> None:
        self.config_path.write_text("[rigctl]\nport = 70000\n", encoding="utf-8")
        result = main([str(self.config_path), "--project-root", str(self.project_root), "--quiet"])
        self.assertEqual(1, result)

    def test_skip_radio_file_check_allows_missing_json(self) -> None:
        missing_path = self.project_root / "missing.toml"
        missing_path.write_text(VALID_TOML.replace("fm_radio.json", "missing.json"), encoding="utf-8")
        result = main([str(missing_path), "--project-root", str(self.project_root), "--skip-radio-file-check", "--quiet"])
        self.assertEqual(0, result)


if __name__ == "__main__":
    unittest.main()
