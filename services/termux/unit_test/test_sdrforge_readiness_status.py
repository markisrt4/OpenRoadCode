# SPDX-License-Identifier: MIT
"""SDRForge readiness is independent of runit's process status."""
import io
from unittest.mock import patch

from services.termux.service_manager import RunitServiceManager


def test_sdrforge_starting_before_http_is_available():
    with patch("services.termux.service_manager.urlopen", side_effect=OSError("refused")):
        state, detail = RunitServiceManager._readiness(
            "openroadcode-sdrforge", "running", "run: service: (pid 123) 2s"
        )
    assert state == "starting"
    assert "Waiting" in detail


def test_sdrforge_ready_after_health_response():
    with patch("services.termux.service_manager.urlopen",
               return_value=io.BytesIO(b'{"status":"ok"}')):
        state, _ = RunitServiceManager._readiness(
            "openroadcode-sdrforge", "running", "run: service: (pid 123) 3s"
        )
    assert state == "ready"


def test_sdrforge_failed_when_api_stays_unavailable():
    with patch("services.termux.service_manager.urlopen", side_effect=OSError("refused")):
        state, _ = RunitServiceManager._readiness(
            "openroadcode-sdrforge", "running", "run: service: (pid 123) 11s"
        )
    assert state == "failed"


def test_sdrforge_stopped_does_not_probe():
    with patch("services.termux.service_manager.urlopen") as probe:
        state, _ = RunitServiceManager._readiness(
            "openroadcode-sdrforge", "stopped", "down: service: 1s"
        )
    assert state == "stopped"
    probe.assert_not_called()


def test_other_services_are_unchanged():
    assert RunitServiceManager._readiness("openroadcode-navigation", "running", "") == (None, None)
