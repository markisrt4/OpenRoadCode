# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify that the shell reports only observed, fresh diagnostics."""

from dataclasses import replace
from unittest import TestCase
from unittest.mock import Mock

from apps.orcUi.performance_status import PerformanceStatusPresenter, performance_status
from ui.system_diagnostics import OrcWorkloadSnapshot, SensorHealthSnapshot, SystemDiagnosticsSnapshot


def sample(**changes):
    return replace(SystemDiagnosticsSnapshot(
        sampled_at_unix_s=100, cpu_percent=20, memory_used_percent=40, disk_used_percent=50,
        workload=OrcWorkloadSnapshot(visibility="visible", cpu_percent=200, cpu_capacity_percent=25),
    ), **changes)


class PerformanceStatusTests(TestCase):
    def test_multicore_workload_and_unobserved_sensor_do_not_warn(self):
        status = performance_status(sample(sensors=(SensorHealthSnapshot("GPS", "gps"),)))
        self.assertEqual(status.text, "● SYS OK")
        self.assertEqual(status.tone, "accent_success")

    def test_pressure_boundaries_and_host_cpu(self):
        for value, tone in ((79.9, "accent_success"), (80, "accent_warning"), (95, "accent_danger")):
            for key in ("cpu_percent", "memory_used_percent", "disk_used_percent"):
                with self.subTest(value=value, key=key):
                    self.assertEqual(performance_status(sample(**{key: value})).tone, tone)
        self.assertEqual(performance_status(sample(workload=OrcWorkloadSnapshot(
            visibility="visible", cpu_percent=640, cpu_capacity_percent=80))).text, "● SYS CPU")

    def test_thermal_and_sensor_severity(self):
        for headroom, tone in ((10, "accent_warning"), (5, "accent_danger")):
            status = performance_status(sample(thermal_headroom_c=headroom))
            self.assertEqual(status.text, "● SYS HOT")
            self.assertEqual(status.tone, tone)
        for state, tone in (("stale", "accent_warning"), ("degraded", "accent_warning"), ("invalid", "accent_danger")):
            self.assertEqual(performance_status(sample(sensors=(SensorHealthSnapshot(
                "GPS", "gps", state=state),))).tone, tone)
        self.assertEqual(performance_status(sample(cpu_percent=80, thermal_headroom_c=5)).text, "● SYS HOT")

    def test_missing_partial_and_stale_readings_are_neutral(self):
        for value in (SystemDiagnosticsSnapshot(), sample(memory_used_percent=None),
                      sample(workload=OrcWorkloadSnapshot(visibility="partial", cpu_capacity_percent=20))):
            self.assertEqual(performance_status(value).tone, "text_muted")
        self.assertEqual(performance_status(sample(cpu_percent=99), stale=True).text, "● SYS OLD")
        self.assertEqual(performance_status(sample()).text, "● SYS OK")

    def test_real_pressure_is_visible_despite_missing_other_data(self):
        self.assertEqual(performance_status(sample(workload=OrcWorkloadSnapshot(), disk_used_percent=96)).text,
                         "● SYS DISK")


class PresenterTests(TestCase):
    def setUp(self):
        self.now = 0
        self.callbacks = []
        self.host = Mock()
        self.host.schedule_ui_callback.side_effect = self.schedule
        self.provider = Mock()
        self.provider.snapshot.return_value = sample()
        self.present = Mock()
        self.presenter = PerformanceStatusPresenter(self.host, self.provider, self.present, clock=lambda: self.now)

    def schedule(self, delay, callback):
        self.assertEqual(delay, 1000)
        self.callbacks.append(callback)
        return len(self.callbacks)

    def test_start_is_idempotent_and_close_cancels_loop(self):
        self.presenter.start()
        self.presenter.start()
        self.assertEqual(len(self.callbacks), 1)
        self.presenter.close()
        self.host.cancel_ui_callback.assert_called_once_with(1)
        self.callbacks[-1]()
        self.assertEqual(self.present.call_count, 1)

    def test_frozen_cache_goes_neutral_and_recovers_on_new_sample(self):
        self.presenter.start()
        self.now = 4
        self.callbacks[-1]()
        self.assertEqual(self.present.call_args.args[0].text, "● SYS OLD")
        self.provider.snapshot.return_value = sample(sampled_at_unix_s=101)
        self.callbacks[-1]()
        self.assertEqual(self.present.call_args.args[0].text, "● SYS OK")

    def test_provider_failure_is_neutral_and_loop_continues(self):
        self.provider.snapshot.side_effect = RuntimeError("unavailable")
        self.presenter.start()
        self.assertEqual(self.present.call_args.args[0].tone, "text_muted")
        self.assertEqual(len(self.callbacks), 1)
