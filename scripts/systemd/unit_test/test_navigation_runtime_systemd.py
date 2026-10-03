# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Static contract tests for navigation systemd installers and wrappers."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SYSTEMD_DIR = PROJECT_ROOT / "scripts" / "systemd"
RUNTIME_DIR = PROJECT_ROOT / "scripts" / "runtime"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_message_broker_installer_enables_expected_service_and_wrapper() -> None:
    installer = _read(SYSTEMD_DIR / "install_message_broker_systemd.sh")
    wrapper = _read(RUNTIME_DIR / "start_message_broker.sh")

    assert 'SERVICE_NAME="openroadcode-message-broker"' in installer
    assert "start_message_broker.sh" in installer
    assert 'systemctl enable "$SERVICE_NAME.service"' in installer
    assert "messaging.zeromq.broker_cli" in wrapper


def test_legacy_zeromq_installer_redirects_to_message_broker() -> None:
    installer = _read(SYSTEMD_DIR / "install_zeromq_systemd.sh")

    assert "deprecated" in installer
    assert "install_message_broker_systemd.sh" in installer
    assert "openroadcode-zmq.service" not in installer


def test_navigation_service_orders_after_broker_and_valhalla() -> None:
    installer = _read(SYSTEMD_DIR / "install_navigation_service_systemd.sh")

    assert "openroadcode-message-broker.service" in installer
    assert "openroadcode-zmq.service" not in installer
    assert "valhalla.service" in installer
    assert "After=" in installer
    assert "Wants=" in installer


def test_runtime_installer_installs_stack_in_dependency_order() -> None:
    installer = _read(SYSTEMD_DIR / "install_navigation_runtime_systemd.sh")

    broker = installer.index("install_message_broker_systemd.sh")
    valhalla = installer.index("install_valhalla_systemd.sh")
    navigation = installer.index("install_navigation_service_systemd.sh")

    assert broker < valhalla < navigation
    assert "openroadcode-message-broker" in installer
    assert "openroadcode-zmq" not in installer
    assert "openroadcode-navigation" in installer
    assert "valhalla" in installer
