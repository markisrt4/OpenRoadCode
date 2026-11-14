"""Contract checks for the optional managed SDRForge service."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from services.termux.service_manager import RunitServiceManager


def test_sdrforge_is_optional_and_profiled() -> None:
    assert "openroadcode-sdrforge" in RunitServiceManager.SERVICES
    assert "openroadcode-sdrforge" not in RunitServiceManager.CORE_STACK
    assert RunitServiceManager.PROFILE_CONFIGS["openroadcode-sdrforge"] == (
        "local", "simulated"
    )


def test_sdrforge_defaults_to_simulation(tmp_path: Path) -> None:
    with patch("services.termux.service_manager.PROFILE_DIR", tmp_path):
        manager = RunitServiceManager()
        assert manager.profile("openroadcode-sdrforge") == "simulated"
        assert manager.available_profiles("openroadcode-sdrforge") == (
            "local", "simulated"
        )
