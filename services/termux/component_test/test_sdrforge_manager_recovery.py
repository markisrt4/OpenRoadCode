# SPDX-License-Identifier: MIT
"""Exercise manager readiness and radio recovery across a local HTTP restart.

Uses a fake supervisor and an ephemeral HTTP port. Never touches Termux runit
or the user's real SDRForge instance.
"""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

import services.termux.service_manager as manager_module
from controllers.radio.adapters.sdrforge_rest_radio_backend import SdrForgeRestRadioBackend
from controllers.radio.component_test.test_sdrforge_restart_recovery import _server
from services.termux.service_manager import RunitServiceManager


def test_supervisor_readiness_and_client_recovery_during_restart():
    with _server() as port:
        backend = SdrForgeRestRadioBackend(f"http://127.0.0.1:{port}", timeout=0.2)
        manager = RunitServiceManager()
        real_urlopen = manager_module.urlopen

        def redirected_health(url, *, timeout):
            if url == "http://127.0.0.1:5570/v1/health":
                url = f"http://127.0.0.1:{port}/v1/health"
            return real_urlopen(url, timeout=timeout)

        def status_at(uptime):
            with patch.object(
                manager,
                "_sv",
                return_value=CompletedProcess(
                    ["sv", "status"], 0, f"run: openroadcode-sdrforge: (pid 123) {uptime}s", ""
                ),
            ):
                with patch.object(manager, "profile", return_value="simulated"):
                    with patch.object(manager, "_input_health", return_value=(None, None)):
                        with patch.object(manager_module, "urlopen", side_effect=redirected_health):
                            return manager.status("openroadcode-sdrforge")

        assert status_at(2).readiness == "ready"
        assert backend.get_frequency() == 94700000

    assert status_at(2).readiness == "starting"
    assert status_at(11).readiness == "failed"
    assert backend.health() is False

    with _server(port):
        assert status_at(12).readiness == "ready"
        assert backend.get_frequency() == 94700000


def test_stopped_supervisor_is_not_ready_even_if_api_is_healthy():
    with _server():
        manager = RunitServiceManager()
        with patch.object(
            manager,
            "_sv",
            return_value=CompletedProcess(
                ["sv", "status"], 0, "down: openroadcode-sdrforge: 1s", ""
            ),
        ):
            with patch.object(manager, "profile", return_value="simulated"):
                with patch.object(manager, "_input_health", return_value=(None, None)):
                    status = manager.status("openroadcode-sdrforge")
        assert status.state == "stopped"
        assert status.readiness == "stopped"
