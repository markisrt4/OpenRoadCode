# SPDX-License-Identifier: MIT
"""Contract tests for the optional SDRForge runit service profile."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from services.termux.service_manager import RunitServiceManager


def test_sdrforge_is_optional_and_profiled() -> None:
    assert "openroadcode-sdrforge" in RunitServiceManager.SERVICES
    assert "openroadcode-sdrforge" not in RunitServiceManager.CORE_STACK
    assert RunitServiceManager.PROFILE_CONFIGS["openroadcode-sdrforge"] == (
        "local", "simulated"
    )


def test_missing_profile_defaults_to_simulation(tmp_path: Path) -> None:
    with patch("services.termux.service_manager.PROFILE_DIR", tmp_path):
        manager = RunitServiceManager()
        assert manager.profile("openroadcode-sdrforge") == "simulated"
        assert manager.profile("openroadcode-navigation") == "local"
        assert manager.profile("openroadcode-automotive") == "local"


def test_explicit_sdrforge_simulation_profile(tmp_path: Path) -> None:
    profile_file = tmp_path / "openroadcode-sdrforge.env"
    profile_file.write_text(
        'export OPENROADCODE_RUNTIME_PROFILE="simulated"\n',
        encoding="utf-8",
    )
    with patch("services.termux.service_manager.PROFILE_DIR", tmp_path):
        assert RunitServiceManager().profile("openroadcode-sdrforge") == "simulated"


def test_direct_hardware_profile_is_rejected(tmp_path: Path) -> None:
    with patch("services.termux.service_manager.PROFILE_DIR", tmp_path):
        with pytest.raises(ValueError, match="Android-authorized USB handoff"):
            RunitServiceManager().set_profile("openroadcode-sdrforge", "local")
