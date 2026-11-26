"""Exercise installer-managed launcher interpreter selection."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def launcher_environment(tmp_path):
    project = tmp_path / "OpenRoadCode"
    project.mkdir()
    launcher = project / "runOrcUi"
    shutil.copyfile(
        Path(__file__).resolve().parents[2] / "runOrcUi",
        launcher,
    )

    home = tmp_path / "home"
    home.mkdir()

    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
    }
    return launcher, env


def fake_python(path, *, is_venv=True, dependencies=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#!{shutil.which('bash')}\n"
        'if [[ "$1" == "-c" ]]; then\n'
        '    case "$2" in\n'
        f"        *sys.base_prefix*) exit {int(not is_venv)} ;;\n"
        f"        *tinycss2*) exit {int(not dependencies)} ;;\n"
        "    esac\n"
        "fi\n"
        'printf "%s\\n" "$@"\n'
    )
    path.chmod(0o755)
    return path


def test_launcher_requires_installer_managed_venv(launcher_environment):
    launcher, env = launcher_environment

    result = subprocess.run(
        ["bash", str(launcher)],
        env=env,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert b"No Python virtual environment found" in result.stderr
    assert b"repository installer" in result.stderr
    assert not (launcher.parent / ".venv").exists()
    assert not (launcher.parent.parent / ".venv").exists()


def test_launcher_reuses_installer_managed_venv(launcher_environment):
    launcher, env = launcher_environment
    interpreter = launcher.parent.parent / ".venv/bin/python"
    fake_python(interpreter)

    for _ in range(2):
        result = subprocess.run(
            ["bash", str(launcher)],
            env=env,
            capture_output=True,
            check=True,
        )

        assert result.stdout.splitlines() == [b"-m", b"apps.orcUi"]
        assert interpreter.is_file()


def test_launcher_rejects_non_venv_python(launcher_environment):
    launcher, env = launcher_environment
    interpreter = fake_python(
        launcher.parent / "python",
        is_venv=False,
    )
    env["PYTHON"] = str(interpreter)

    result = subprocess.run(
        ["bash", str(launcher)],
        env=env,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert b"not running in a virtual environment" in result.stderr


def test_launcher_reports_missing_dependencies(launcher_environment):
    launcher, env = launcher_environment
    interpreter = fake_python(
        launcher.parent.parent / ".venv/bin/python",
        dependencies=False,
    )
    env["PYTHON"] = str(interpreter)

    result = subprocess.run(
        ["bash", str(launcher)],
        env=env,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert b"Missing required ORC UI dependencies" in result.stderr
    assert b"requests/tinycss2" in result.stderr
