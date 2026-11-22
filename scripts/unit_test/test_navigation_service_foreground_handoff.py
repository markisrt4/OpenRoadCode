"""Foreground navigation temporarily owns the installed service's ports."""

import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/runtime/start_navigation_service.sh"


def _executable(path: Path, content: str) -> Path:
    path.write_text("#!/usr/bin/env bash\nset -eu\n" + content)
    path.chmod(0o755)
    return path


def test_active_installed_service_is_stopped_and_restored(tmp_path):
    log = tmp_path / "calls.log"
    systemctl = _executable(tmp_path / "systemctl", "exit 0\n")
    control = _executable(
        tmp_path / "control", 'echo "control $*" >> "$HANDOFF_LOG"\n'
    )
    python = _executable(
        tmp_path / "python", 'echo "python $*" >> "$HANDOFF_LOG"\nexit 7\n'
    )
    env = os.environ | {
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "HANDOFF_LOG": str(log),
        "OPENROADCODE_PYTHON": str(python),
        "OPENROADCODE_SERVICE_CONTROL": str(control),
    }
    env.pop("OPENROADCODE_INSTALLED_SERVICE", None)

    result = subprocess.run(
        ["bash", str(SCRIPT), "--profile", "local"], env=env,
        capture_output=True, text=True, timeout=10,
    )

    assert result.returncode == 7
    calls = log.read_text().splitlines()
    assert calls[0] == "control stop openroadcode-navigation.service"
    assert "navigation_service_cli" in calls[1]
    assert calls[2] == "control start openroadcode-navigation.service"
    assert "Temporarily stopping" in result.stdout
    assert "Restoring installed" in result.stdout


def test_systemd_invocation_never_hands_off_its_own_unit(tmp_path):
    log = tmp_path / "calls.log"
    _executable(tmp_path / "systemctl", "exit 0\n")
    python = _executable(
        tmp_path / "python", 'echo "python $*" >> "$HANDOFF_LOG"\n'
    )
    control = _executable(
        tmp_path / "control", 'echo "control $*" >> "$HANDOFF_LOG"\n'
    )
    env = os.environ | {
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "HANDOFF_LOG": str(log),
        "OPENROADCODE_INSTALLED_SERVICE": "1",
        "OPENROADCODE_PYTHON": str(python),
        "OPENROADCODE_SERVICE_CONTROL": str(control),
    }

    result = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )

    assert result.returncode == 0
    calls = log.read_text().splitlines()
    assert len(calls) == 1 and calls[0].startswith("python ")
