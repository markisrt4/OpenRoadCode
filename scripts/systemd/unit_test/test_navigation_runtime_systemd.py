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


def test_navigation_service_orders_after_broker_and_valhalla() -> None:
    installer = _read(SYSTEMD_DIR / "install_navigation_service_systemd.sh")

    assert "openroadcode-message-broker.service" in installer
    assert "openroadcode-zmq.service" not in installer
    assert "valhalla.service" in installer
    assert "After=" in installer
    assert "Wants=network.target openroadcode-message-broker.service valhalla.service" in installer
    assert "Environment=OPENROADCODE_RUNTIME_CONFIG=$RUNTIME_CONFIG" in installer


def test_automotive_service_passes_installer_runtime_overrides() -> None:
    installer = _read(SYSTEMD_DIR / "install_automotive_service_systemd.sh")

    assert "Environment=OPENROADCODE_PYTHON=$PYTHON_BIN" in installer
    assert "Environment=OPENROADCODE_RUNTIME_CONFIG=$RUNTIME_CONFIG" in installer
    assert "EnvironmentFile=-/var/lib/openroadcode/service-profiles/openroadcode-runtime.env" in installer


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


def test_valhalla_runs_as_the_non_root_runtime_user() -> None:
    installer = _read(SYSTEMD_DIR / "install_valhalla_systemd.sh")

    assert 'RUN_USER="${SUDO_USER:-${USER:-}}"' in installer
    assert "User=$RUN_USER" in installer
    assert '[[ -z "$RUN_USER" || "$RUN_USER" == "root" ]]' in installer
