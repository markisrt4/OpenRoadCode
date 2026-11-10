# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Performance diagnostics emit bounded, private lifecycle and recovery records."""

import json
import logging
from unittest.mock import Mock, patch

import pytest

from common.logging.structured import JsonFormatter, validate_event
from services.common.system_performance_monitor import SystemPerformanceMonitor
from ui.system_diagnostics import OrcWorkloadSnapshot, SystemDiagnosticsSnapshot


def monitor():
    controller, process, services, sensors, battery = (Mock() for _ in range(5))
    controller.snapshot.return_value = SystemDiagnosticsSnapshot(cpu_percent=42)
    process.sample.return_value = OrcWorkloadSnapshot()
    services.sample.return_value = ()
    services.status = "observed"
    sensors.snapshots.return_value = ()
    sensors.status = "listening"
    battery.snapshot.return_value = None
    result = SystemPerformanceMonitor(
        controller, process_sampler=process, service_sampler=services,
        sensor_monitor=sensors, battery_monitor=battery,
    )
    return result, controller, process, services


def records(caplog):
    result = [json.loads(JsonFormatter().format(r)) for r in caplog.records
              if r.name == "runtime.performance"]
    for record in result:
        validate_event(record)
    serialized = json.dumps(result)
    for private in ("private", "cpu_percent", "rss_bytes", "service_status", "command"):
        assert private not in serialized
    return result


@pytest.mark.parametrize("stage", ["host", "process", "services"])
def test_worker_reports_failure_and_recovery_once_without_telemetry(caplog, stage):
    caplog.set_level(logging.INFO)
    runtime, host, process, services = monitor()
    runtime._operation_id = "sampling-operation"
    sampler = {"host": host.snapshot, "process": process.sample, "services": services.sample}[stage]
    success = sampler.return_value
    sampler.side_effect = [OSError("private /path and command"), OSError("private details"),
                           success, success]
    runtime._stop = Mock()
    runtime._stop.is_set.side_effect = [False] * 4 + [True]
    runtime._run()
    emitted = records(caplog)
    assert [r["event"] for r in emitted] == ["sampler.failed", "sampler.recovered"]
    assert [r["level"] for r in emitted] == ["WARNING", "INFO"]
    assert {r["sampler"] for r in emitted} == {stage}
    assert {r["operation_id"] for r in emitted} == {"sampling-operation"}
    assert emitted[0]["exception_type"] == "OSError"
    assert runtime.payload()["error"] is None
    assert runtime.history()


def test_repeated_lifecycle_calls_stay_quiet_and_restart_gets_new_id(caplog):
    caplog.set_level(logging.INFO)
    runtime, *_ = monitor()
    with patch("services.common.system_performance_monitor.threading.Thread"):
        runtime.start()
        runtime.start()
        runtime.close()
        runtime.close()
        runtime.start()
        runtime.close()
    emitted = records(caplog)
    assert [r["event"] for r in emitted] == ["sampler.started", "sampler.stopped"] * 2
    assert emitted[0]["operation_id"] == emitted[1]["operation_id"]
    assert emitted[2]["operation_id"] == emitted[3]["operation_id"]
    assert emitted[0]["operation_id"] != emitted[2]["operation_id"]


def test_worker_start_failure_is_logged_and_cleans_up_owned_monitors(caplog):
    caplog.set_level(logging.INFO)
    runtime, *_ = monitor()
    with patch("services.common.system_performance_monitor.threading.Thread") as worker:
        worker.return_value.start.side_effect = RuntimeError("private device path")
        with pytest.raises(RuntimeError):
            runtime.start()
    emitted = records(caplog)
    assert [r["event"] for r in emitted] == ["sampler.failed"]
    assert emitted[0]["sampler"] == "worker"
    assert runtime._thread is None
    runtime._sensor_monitor.close.assert_called_once()
    runtime._battery_monitor.close.assert_called_once()
