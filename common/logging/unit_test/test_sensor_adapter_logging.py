# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Real adapter boundaries tested with synthetic GPS/I2C drivers."""

import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from common.logging.structured import operation
from common.logging.unit_test.test_device_logging import PRIVATE, records
from hardware_io.environmental.bmp3xx import Bmp3xx
from hardware_io.imu.mpu6050_imu import Mpu6050Imu


@pytest.mark.parametrize("kind", ["bmp", "imu"])
def test_i2c_start_failure_recovery_and_polling_are_private(caplog, kind):
    caplog.set_level(logging.DEBUG)
    sensor = SimpleNamespace(pressure=1013.25, temperature=20, acceleration=(1, 2, 3), gyro=(1, 2, 3))
    constructor = Mock(side_effect=[OSError(PRIVATE), OSError(PRIVATE), sensor])
    if kind == "bmp":
        module, driver = "adafruit_bmp3xx", SimpleNamespace(BMP3XX_I2C=constructor)
        adapter = Bmp3xx(i2c=Mock())
        read = adapter.get_pressure_pa
    else:
        module, driver = "adafruit_mpu6050", SimpleNamespace(MPU6050=constructor)
        adapter = Mpu6050Imu(i2c_bus=Mock())
        read = adapter.get_acceleration_mps2
    with patch.dict("sys.modules", {module: driver}), operation("i2c-session"):
        for _ in range(2):
            with pytest.raises((OSError, RuntimeError)):
                adapter.start()
        adapter.start()
        for _ in range(3):
            read()
        adapter.stop()
    emitted = records(caplog, "environmental.")
    assert len([r for r in emitted if r["event"] == "sensor.failed"]) == 1
    assert len([r for r in emitted if r["event"] == "sensor.recovered"]) == 1
    assert all(r["operation_id"] == "i2c-session" for r in emitted)
    assert [r["state"] for r in emitted if r["event"] == "sensor.state_changed"] == ["started", "stopped"]


def gps_adapter():
    # Load an isolated copy so CI needs neither gpsd bindings nor a live gpsd.
    gps = SimpleNamespace(gps=type("GpsSession", (), {}), WATCH_ENABLE=1, WATCH_NEWSTYLE=2)
    client = SimpleNamespace(dictwrapper=dict)
    path = Path(__file__).resolve().parents[3] / "hardware_io/gps/gps_reader.py"
    spec = importlib.util.spec_from_file_location("logging_test_gps", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict("sys.modules", {"gps": gps, "gps.client": client}):
        spec.loader.exec_module(module)
    return module


def test_gps_address_report_and_callback_errors_never_reach_logs(caplog):
    caplog.set_level(logging.DEBUG)
    module = gps_adapter()
    received = Mock(side_effect=OSError(PRIVATE))
    reader = module.GpsReader(received, host=PRIVATE, port=PRIVATE)
    reports = [{"class": "TPV", "lat": 42.8028, "lon": -83.0127}]
    with patch.object(module, "_Python3GpsSession", return_value=reports), operation("gps-session"):
        reader.open()
        reader._run()
        reader._run()
        received.side_effect = None
        reader._run()
    emitted = records(caplog, "navigation.gps")
    assert len([r for r in emitted if r["event"] == "gps.failed"]) == 1
    assert len([r for r in emitted if r["event"] == "gps.recovered"]) == 1
    assert received.call_count == 3


def test_gps_thread_carries_start_operation(caplog):
    caplog.set_level(logging.DEBUG)
    module = gps_adapter()
    reader = module.GpsReader(Mock(), host=PRIVATE)
    with patch.object(module, "_Python3GpsSession", return_value=[]), \
         patch.object(module.threading, "Thread") as thread:
        with operation("gps-start"):
            reader.start()
        target = thread.call_args.kwargs["target"]
        args = thread.call_args.kwargs["args"]
        target(*args)
    emitted = records(caplog, "navigation.gps")
    assert all(r["operation_id"] == "gps-start" for r in emitted)


def test_expected_gps_shutdown_does_not_report_failure(caplog):
    caplog.set_level(logging.DEBUG)
    module = gps_adapter()
    reader = module.GpsReader(Mock(side_effect=OSError(PRIVATE)))
    reader._session = [{"class": "TPV", "lat": 42.8028}]
    reader._stop_event.set()
    reader._run()
    assert not any(r["event"] == "gps.failed" for r in records(caplog, "navigation.gps"))
