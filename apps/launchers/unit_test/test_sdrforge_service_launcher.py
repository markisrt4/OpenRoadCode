# SPDX-License-Identifier: MIT
"""Non-owning SDRForge launcher contract tests."""

from __future__ import annotations

import io
import json
from unittest.mock import patch

import pytest

from apps.launchers.sdrforge_service_launcher import SdrForgeServiceLauncher


def test_healthy_service_is_ready_without_starting_processes() -> None:
    launcher = SdrForgeServiceLauncher()
    messages: list[str] = []
    with patch("apps.launchers.sdrforge_service_launcher.urlopen") as open_url:
        open_url.return_value.__enter__.return_value = io.BytesIO(
            json.dumps({"status": "ok"}).encode()
        )
        assert launcher.toggle(":1", messages.append)
    assert messages == ["SDRForge service ready"]


def test_unavailable_service_is_not_silently_started() -> None:
    launcher = SdrForgeServiceLauncher()
    with patch("apps.launchers.sdrforge_service_launcher.urlopen", side_effect=OSError("offline")):
        assert not launcher.is_running()
        with pytest.raises(RuntimeError, match="SDRForge service unavailable"):
            launcher.launch(":1")


def test_stop_does_not_stop_shared_service() -> None:
    launcher = SdrForgeServiceLauncher()
    messages: list[str] = []
    with patch("apps.launchers.sdrforge_service_launcher.urlopen") as open_url:
        launcher.stop(":1", messages.append)
        open_url.assert_not_called()
    assert messages == ["SDRForge remains managed by its service"]
