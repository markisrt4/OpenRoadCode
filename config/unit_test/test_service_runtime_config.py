# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for system service runtime TOML parsing."""

from pathlib import Path

import pytest

from config.service_runtime_config import (
    ServiceRuntimeConfigError,
    ServiceRuntimeConfigParser,
)


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "runtime.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_nested_navigation_pipeline_is_parsed(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
[messaging]
publisher_endpoint = "tcp://127.0.0.1:6001"
subscriber_endpoint = "tcp://127.0.0.1:6002"

[services.navigation]
enabled = true
rate_hz = 20.0
command_endpoint = "tcp://127.0.0.1:6003"

[services.navigation.inputs.imu]
source = "simulation"
device = "mpu6050"
address = 0x69

[services.navigation.inputs.imu.simulation]
profile = "stationary"

[services.navigation.inputs.gps]
source = "device"
device = "gpsd"
host = "192.0.2.10"
port = "2948"

[services.navigation.inputs.gps.simulation]
profile = "driving"
latitude_deg = 42.5
longitude_deg = -83.1
speed_mps = 12.25
course_deg = 91.0

[services.navigation.solution]
algorithm = "complementary_filter"

[services.navigation.solution.complementary_filter]
time_constant_s = 0.75
heading_reference = "relative"

[services.navigation.publish]
enabled = true
source = "test-navigation"
""",
    )

    config = ServiceRuntimeConfigParser(path).load()

    assert config.messaging.publisher_endpoint == "tcp://127.0.0.1:6001"
    assert config.messaging.subscriber_endpoint == "tcp://127.0.0.1:6002"
    assert config.navigation.enabled
    assert config.navigation.rate_hz == 20.0
    assert config.navigation.command_endpoint == "tcp://127.0.0.1:6003"
    assert config.navigation.imu.source == "simulation"
    assert config.navigation.imu.device == "mpu6050"
    assert config.navigation.imu.address == 0x69
    assert config.navigation.imu.simulation.profile == "stationary"
    assert config.navigation.gps.source == "device"
    assert config.navigation.gps.device == "gpsd"
    assert config.navigation.gps.host == "192.0.2.10"
    assert config.navigation.gps.port == "2948"
    assert config.navigation.gps.simulation.latitude_deg == 42.5
    assert config.navigation.solution.algorithm == "complementary_filter"
    assert config.navigation.solution.complementary_filter.time_constant_s == 0.75
    assert config.navigation.publish.source == "test-navigation"


def test_simulation_sources_are_independently_selectable(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
[services.navigation.inputs.imu]
source = "device"
device = "mpu6050"

[services.navigation.inputs.gps]
source = "simulation"

[services.navigation.inputs.gps.simulation]
profile = "stationary"
latitude_deg = 42.0
longitude_deg = -83.0
speed_mps = 0.0
course_deg = 0.0
""",
    )

    config = ServiceRuntimeConfigParser(path).load()

    assert config.navigation.imu.source == "device"
    assert config.navigation.gps.source == "simulation"
    assert config.navigation.gps.simulation.profile == "stationary"


def test_defaults_build_a_device_navigation_pipeline(tmp_path: Path) -> None:
    config = ServiceRuntimeConfigParser(_write(tmp_path, "")).load()

    assert config.navigation.enabled
    assert config.navigation.imu.source == "device"
    assert config.navigation.imu.device == "mpu6050"
    assert config.navigation.gps.source == "device"
    assert config.navigation.gps.device == "gpsd"
    assert config.navigation.solution.algorithm == "complementary_filter"
    assert config.navigation.publish.enabled


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (
            "[services.navigation.inputs.imu]\nsource = 'magic'\n",
            "services.navigation.inputs.imu.source must be device or simulation",
        ),
        (
            "[services.navigation]\nrate_hz = 0\n",
            "services.navigation.rate_hz must be greater than zero",
        ),
        (
            "[services.navigation.solution]\nalgorithm = 'telepathy'\n",
            "services.navigation.solution.algorithm must be complementary_filter",
        ),
        (
            "[services.navigation.inputs.imu]\naddress = 255\n",
            "services.navigation.inputs.imu.address must be a valid 7-bit I2C address",
        ),
    ],
)
def test_invalid_navigation_configuration_is_rejected(
    tmp_path: Path,
    text: str,
    message: str,
) -> None:
    with pytest.raises(ServiceRuntimeConfigError, match=message):
        ServiceRuntimeConfigParser(_write(tmp_path, text)).load()
