# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Cross-platform contracts for OpenRoadCode service supervision."""

from pathlib import Path

from services.linux.systemd_service_manager import SystemdServiceManager
from services.termux.service_manager import RunitServiceManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNIT_ROOT = PROJECT_ROOT / "scripts" / "runit"


def test_managed_service_inventory_and_core_order_match() -> None:
    assert RunitServiceManager.SERVICES == SystemdServiceManager.SERVICES
    assert RunitServiceManager.CORE_STACK == SystemdServiceManager.CORE_STACK


def test_every_termux_managed_service_has_definition_and_rotating_log() -> None:
    generic_log = (RUNIT_ROOT / "log" / "run").read_text(encoding="utf-8")
    assert "svlogd" in generic_log
    for service in ("openroadcode-service-manager", *RunitServiceManager.SERVICES):
        assert (RUNIT_ROOT / service / "run").is_file()


def test_termux_services_are_down_by_default_except_control_plane() -> None:
    for service in RunitServiceManager.SERVICES:
        assert (RUNIT_ROOT / service / "down").is_file()
    assert not (RUNIT_ROOT / "openroadcode-service-manager" / "down").exists()


def test_termux_direct_starts_request_required_supervisors() -> None:
    navigation = (RUNIT_ROOT / "openroadcode-navigation" / "run").read_text(
        encoding="utf-8"
    )
    automotive = (RUNIT_ROOT / "openroadcode-automotive" / "run").read_text(
        encoding="utf-8"
    )
    assert "sv up openroadcode-message-broker" in navigation
    assert "sv up openroadcode-valhalla" in navigation
    assert "sv up openroadcode-message-broker" in automotive


def test_termux_runtime_and_service_profiles_follow_linux_precedence() -> None:
    for service in ("openroadcode-navigation", "openroadcode-automotive"):
        run_script = (RUNIT_ROOT / service / "run").read_text(encoding="utf-8")
        runtime_index = run_script.index("openroadcode-runtime.env")
        service_index = run_script.index(f"{service}.env")
        assert runtime_index < service_index
        assert run_script.count("set -a") == 2


def test_termux_core_helper_uses_shared_dependency_order() -> None:
    helper = (RUNIT_ROOT / "manage_core.sh").read_text(encoding="utf-8")
    positions = [helper.index(service) for service in RunitServiceManager.CORE_STACK]
    assert positions == sorted(positions)
