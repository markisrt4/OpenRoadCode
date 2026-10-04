# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Runtime logging contracts without real supervisors, processes, or power actions."""

import json
import logging
import signal
import subprocess
from unittest.mock import Mock, patch

import pytest

from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.process_manager import terminate_process
from common.logging.structured import JsonFormatter, current_operation, operation, validate_event
from config.application_config import (
    ApplicationConfig,
    ApplicationsConfig,
    ApplicationType,
    BrowserConfig,
    StartupPolicy,
)
from controllers.application_runtime import AppRuntimeManager
from controllers.system.system_lifecycle_controller import SystemLifecycleController
from services.linux.systemd_service_manager import SystemdServiceManager
from services.termux.service_manager import RunitServiceManager


def events(caplog):
    result = [
        json.loads(JsonFormatter().format(record))
        for record in caplog.records
        if record.name.startswith("runtime.")
    ]
    for item in result:
        validate_event(item)
    assert "private" not in json.dumps(result)
    return result


class Launcher:
    def __init__(self):
        self.running = False
        self.calls = []
        self.error = None

    def launch(self, display, set_status=None):
        if self.error:
            raise self.error
        self.calls.append("launch")
        self.running = True

    def stop(self, display, set_status=None):
        if self.error:
            raise self.error
        self.calls.append("stop")
        self.running = False

    def prepare(self, display, set_status=None):
        self.launch(display, set_status)

    def toggle(self, display, set_status=None):
        self.running = not self.running
        return self.running

    def is_running(self):
        return self.running


def manager(*, policy=StartupPolicy.LAZY, second=False):
    keys = ("weather", "earth") if second else ("weather",)
    config = ApplicationsConfig(
        browser=BrowserConfig(),
        apps=tuple(
            ApplicationConfig(
                key=key,
                type=ApplicationType.BROWSER,
                startup=policy,
                url="https://private-url/?token=private",
                profile=key,
            )
            for key in keys
        ),
    )
    result = AppRuntimeManager(config, remote_display=":1")
    launchers = []
    for key in keys:
        launcher = Launcher()
        result.register(key, launcher)
        launchers.append(launcher)
    return result, launchers


def test_restart_correlates_nested_show_without_logging_launch_arguments(caplog):
    caplog.set_level(logging.INFO)
    runtime, (launcher,) = manager()
    launcher.running = True
    runtime.restart("weather")
    assert launcher.calls == ["stop", "launch"]
    emitted = events(caplog)
    assert [item["action"] for item in emitted] == ["restart", "show", "show", "restart"]
    assert len({item["operation_id"] for item in emitted}) == 1
    assert current_operation() is None


def test_failed_app_launch_does_not_log_completion_or_mark_visible(caplog):
    caplog.set_level(logging.INFO)
    runtime, (launcher,) = manager()
    launcher.error = RuntimeError("private URL and command line")
    with pytest.raises(RuntimeError):
        runtime.show("weather")
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == ["app.action.requested", "app.action.failed"]
    assert not runtime.is_visible("weather")


def test_preload_thread_keeps_request_operation_and_reports_failure_counts(caplog):
    caplog.set_level(logging.INFO)
    runtime, launchers = manager(policy=StartupPolicy.PRELOAD, second=True)
    launchers[0].error = RuntimeError("private startup")
    with operation("startup-operation"):
        runtime.start_background_apps()
    runtime._preload_thread.join(timeout=2)
    assert not runtime._preload_thread.is_alive()
    emitted = events(caplog)
    assert all(item["operation_id"] == "startup-operation" for item in emitted)
    assert emitted[-1]["event"] == "preload.finished"
    assert emitted[-1]["failed_count"] == 1 and emitted[-1]["completed_count"] == 1
    assert launchers[1].running


def test_cleanup_continues_after_failure_and_reports_partial_result(caplog):
    caplog.set_level(logging.INFO)
    runtime, launchers = manager(second=True)
    launchers[0].error = RuntimeError("private cleanup")
    launchers[1].running = True
    runtime.stop_all()
    assert not launchers[1].running
    emitted = events(caplog)
    summary = next(item for item in emitted if item["event"] == "app.cleanup_finished")
    assert summary["failed_count"] == 1 and summary["app_count"] == 2
    assert summary["level"] == "WARNING"
    assert "app.cleanup_failed" in [item["event"] for item in emitted]


def test_running_state_polling_stays_quiet_until_transition(caplog):
    caplog.set_level(logging.INFO)
    runtime, (launcher,) = manager()
    launcher.running = True
    assert runtime.is_running("weather")
    assert runtime.is_running("weather")
    assert not events(caplog)
    launcher.running = False
    assert not runtime.is_running("weather")
    assert not runtime.is_running("weather")
    emitted = events(caplog)
    assert len(emitted) == 1 and emitted[0]["event"] == "app.running_changed"


@pytest.mark.parametrize(
    "manager_type,module,active_output",
    [
        (SystemdServiceManager, "services.linux.systemd_service_manager", "active\n"),
        (
            RunitServiceManager,
            "services.termux.service_manager",
            "run: private raw supervisor output\n",
        ),
    ],
)
def test_supervisor_control_and_status_share_id_and_polling_is_quiet(
    caplog, tmp_path, manager_type, module, active_output
):
    caplog.set_level(logging.INFO)
    runtime = manager_type()

    def run(command, **kwargs):
        action = command[2] if command[0] == "sudo" else command[1]
        output = active_output if action in {"is-active", "status"} else "private output"
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    with (
        patch(module + ".PROFILE_DIR", tmp_path),
        patch(module + ".subprocess.run", side_effect=run),
    ):
        result = runtime.restart("openroadcode-message-broker")
        assert result.state == "running"
        baseline = events(caplog)
        runtime.status("openroadcode-message-broker")
        assert events(caplog) == baseline
    assert len({item["operation_id"] for item in baseline}) == 1
    assert {item["event"] for item in baseline} >= {
        "service.action.requested",
        "supervisor.command_completed",
        "service.status_observed",
        "service.action.completed",
    }


@pytest.mark.parametrize(
    "manager_type,module",
    [
        (SystemdServiceManager, "services.linux.systemd_service_manager"),
        (RunitServiceManager, "services.termux.service_manager"),
    ],
)
@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(5, ["private command"], stderr="private output"),
        subprocess.TimeoutExpired(["private command"], 5),
        FileNotFoundError("private executable"),
    ],
)
def test_supervisor_failures_are_safe_and_do_not_claim_completion(
    caplog, manager_type, module, error
):
    caplog.set_level(logging.INFO)
    with patch(module + ".subprocess.run", side_effect=error):
        with pytest.raises(type(error)):
            manager_type().start("openroadcode-navigation")
    emitted = events(caplog)
    assert "service.action.completed" not in [item["event"] for item in emitted]
    failures = [item for item in emitted if item["event"].endswith("failed")]
    assert len(failures) == 2
    assert all(item["exception_type"] == type(error).__name__ for item in failures)
    if isinstance(error, subprocess.CalledProcessError):
        assert all(item["returncode"] == 5 for item in failures)


def test_status_query_errors_log_once_then_recover(caplog, tmp_path):
    caplog.set_level(logging.INFO)
    runtime = SystemdServiceManager()
    error = subprocess.TimeoutExpired(["private command"], 8)
    with (
        patch("services.linux.systemd_service_manager.PROFILE_DIR", tmp_path),
        patch.object(
            runtime,
            "_systemctl",
            side_effect=[
                error,
                error,
                subprocess.CompletedProcess([], 0, "active\n", ""),
                subprocess.CompletedProcess([], 0, "active / running", ""),
            ],
        ),
    ):
        for _ in range(2):
            with pytest.raises(subprocess.TimeoutExpired):
                runtime.status("openroadcode-message-broker")
        runtime.status("openroadcode-message-broker")
    assert [item["event"] for item in events(caplog)] == [
        "service.status_failed",
        "service.status_recovered",
        "service.status_observed",
    ]


def test_rejected_service_identifier_is_not_logged(caplog):
    caplog.set_level(logging.INFO)
    with pytest.raises(ValueError):
        SystemdServiceManager().start("private-service-input")
    emitted = events(caplog)
    assert all(item["service"] is None for item in emitted)


def test_owned_browser_exit_logs_pid_code_and_launch_operation_once(caplog, tmp_path):
    caplog.set_level(logging.INFO)
    browser = BrowserKioskLauncher(url="https://private-url", log_file=tmp_path / "browser.log")
    browser._process = Mock(pid=4321)
    browser._process.poll.return_value = 7
    browser._launch_operation_id = "browser-launch"
    with patch("apps.launchers.browser_launcher.is_process_running", return_value=False):
        assert not browser.is_running()
        assert not browser.is_running()
    emitted = events(caplog)
    assert len(emitted) == 1 and emitted[0]["event"] == "browser.exited"
    assert emitted[0]["child_pid"] == 4321 and emitted[0]["exit_code"] == 7
    assert emitted[0]["operation_id"] == "browser-launch"


def test_forced_child_termination_logs_numeric_context(caplog):
    caplog.set_level(logging.INFO)
    process = Mock(pid=4321)
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired(["private command"], 5), -9]
    with (
        patch("apps.launchers.process_manager.os.getpgid", return_value=4321),
        patch("apps.launchers.process_manager.os.killpg") as kill,
    ):
        terminate_process(process)
    assert kill.call_args_list[-1].args == (4321, signal.SIGKILL)
    emitted = events(caplog)
    assert "process.kill_forced" in [item["event"] for item in emitted]
    assert len({item["operation_id"] for item in emitted}) == 1
    assert (
        next(item for item in emitted if item["event"] == "process.exit_observed")["exit_code"]
        == -9
    )


@pytest.mark.parametrize("action", ["request_restart_ui", "request_poweroff"])
def test_deferred_host_dispatch_keeps_request_id_without_real_os_action(caplog, action):
    caplog.set_level(logging.INFO)
    execv, popen = Mock(), Mock()
    host = SystemLifecycleController(
        executable="/private/python",
        execv=execv,
        which=lambda _name: "/private/systemctl",
        popen=popen,
    )
    getattr(host, action)()
    getattr(host, action)()
    assert host.execute_requested_action()
    assert not host.execute_requested_action()
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == [
        "host.action_requested",
        "host.dispatch_requested",
        "host.action_dispatched",
    ]
    assert len({item["operation_id"] for item in emitted}) == 1


def test_failed_host_dispatch_has_no_dispatched_event(caplog):
    caplog.set_level(logging.INFO)
    host = SystemLifecycleController(execv=Mock(side_effect=OSError("private argv")))
    host.request_restart_ui()
    with pytest.raises(OSError):
        host.execute_requested_action()
    assert events(caplog)[-1]["event"] == "host.dispatch_failed"


@pytest.mark.parametrize(
    "module",
    ["services.linux.systemd_service_manager_http", "services.termux.service_manager_http"],
)
def test_service_manager_entry_configures_logging_and_logs_safe_startup_failure(caplog, module):
    import importlib

    http = importlib.import_module(module)
    caplog.set_level(logging.INFO)
    with (
        patch.object(http, "configure_logging") as configure,
        patch.object(http, "_run_server", side_effect=OSError("private binding")),
    ):
        with pytest.raises(OSError):
            http.main()
    configure.assert_called_once()
    assert events(caplog)[0]["event"] == "manager.failed"


def test_core_failure_identifies_service_and_preserves_command_order(caplog):
    caplog.set_level(logging.INFO)
    failure = subprocess.CalledProcessError(
        3, ["private command"], stderr="private supervisor output"
    )
    with patch(
        "services.linux.systemd_service_manager.subprocess.run",
        side_effect=[subprocess.CompletedProcess([], 0, "private output", ""), failure],
    ) as run:
        with pytest.raises(subprocess.CalledProcessError):
            SystemdServiceManager().start_core()
    assert [call.args[0][-1] for call in run.call_args_list] == [
        "openroadcode-message-broker.service",
        "openroadcode-navigation.service",
    ]
    emitted = events(caplog)
    failure_event = next(item for item in emitted if item["event"] == "supervisor.command_failed")
    assert failure_event["service"] == "openroadcode-navigation"
    assert not any(item["event"] == "service.action.completed" for item in emitted)
    assert len({item["operation_id"] for item in emitted}) == 1


def test_runit_input_health_changes_are_safe_and_transition_only(caplog, tmp_path):
    caplog.set_level(logging.INFO)
    runtime = RunitServiceManager()
    with (
        patch("services.termux.service_manager.PROFILE_DIR", tmp_path),
        patch.object(
            runtime,
            "_sv",
            return_value=subprocess.CompletedProcess([], 0, "run: private details", ""),
        ),
        patch.object(
            runtime,
            "_input_health",
            side_effect=[
                ("waiting", "private phone"),
                ("waiting", "private phone"),
                ("connected", "private bridge"),
            ],
        ),
    ):
        for _ in range(3):
            runtime.status("openroadcode-navigation")
    emitted = events(caplog)
    assert [item["input_state"] for item in emitted] == ["waiting", "connected"]


def test_systemd_failed_unit_is_visible_even_when_mapped_to_stopped(caplog, tmp_path):
    caplog.set_level(logging.INFO)
    runtime = SystemdServiceManager()
    with (
        patch("services.linux.systemd_service_manager.PROFILE_DIR", tmp_path),
        patch.object(
            runtime,
            "_systemctl",
            side_effect=[
                subprocess.CompletedProcess([], 3, "failed\n", ""),
                subprocess.CompletedProcess([], 0, "failed\nfailed\nenabled", ""),
            ],
        ),
    ):
        status = runtime.status("openroadcode-navigation")
    assert status.state == "stopped"
    emitted = events(caplog)
    assert emitted[0]["supervisor_failed"] is True and emitted[0]["level"] == "WARNING"


def test_profile_validation_does_not_log_untrusted_profile(caplog):
    caplog.set_level(logging.INFO)
    with pytest.raises(ValueError):
        RunitServiceManager().set_profile("openroadcode-navigation", "private-profile")
    emitted = events(caplog)
    assert emitted[-1]["event"] == "service.action.failed"


def test_host_clear_and_unavailable_poweroff_do_not_claim_dispatch(caplog):
    caplog.set_level(logging.INFO)
    host = SystemLifecycleController(which=lambda _name: None)
    host.request_restart_ui()
    host.clear()
    host.clear()
    assert not host.execute_requested_action()
    host.request_poweroff()
    assert not host.execute_requested_action()
    emitted = events(caplog)
    assert [item["event"] for item in emitted] == [
        "host.action_requested",
        "host.action_cleared",
        "host.action_requested",
        "host.dispatch_requested",
        "host.action_unavailable",
    ]


def test_restricted_install_can_import_http_and_write_logs_without_checkout(tmp_path):
    import os
    from pathlib import Path
    import shutil
    import sys

    root = Path(__file__).resolve().parents[3]
    script = (root / "scripts/systemd/install_service_manager_systemd.sh").read_text()
    manifest = next(line for line in script.splitlines() if line.startswith("for package in "))
    packages = manifest.removeprefix("for package in ").removesuffix("; do").split()
    deployed = tmp_path / "installed"
    for package in packages:
        for source in (root / package).glob("*.py"):
            target = deployed / source.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    # The installer explicitly ships this namespace-package dependency.
    assert '"$PROJECT_ROOT/common/xdg_paths.py"' in script
    shutil.copyfile(root / "common/xdg_paths.py", deployed / "common/xdg_paths.py")
    log_dir = tmp_path / "logs"
    code = (
        "import logging; import services.linux.systemd_service_manager_http; "
        "from common.logging.structured import configure_logging,event; "
        "configure_logging(stderr=False); "
        "event(logging.getLogger('runtime.services.http'),logging.INFO,'install.smoke','Installed logger ready')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=dict(os.environ, PYTHONPATH=str(deployed), ORC_LOG_DIR=str(log_dir)),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    validate_event(json.loads((log_dir / "orc.jsonl").read_text()))
