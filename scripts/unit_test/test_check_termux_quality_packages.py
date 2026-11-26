"""Regression coverage for native Termux package compatibility notices."""

import subprocess

from scripts import check_termux_quality_packages as checker


def test_only_native_platform_notices_can_clear_pip_failure(monkeypatch, capsys):
    notice = "numpy 2.5.4 is not supported on this platform"
    dependency_error = "example 1 requires missing-package, which is not installed."
    monkeypatch.setattr(checker, "native_platform_notices", lambda: {notice})
    result = subprocess.CompletedProcess([], 1, notice + "\n", "")
    monkeypatch.setattr(checker.subprocess, "run", lambda *_args, **_kwargs: result)

    assert checker.check_packages() == 0
    assert "Using linked Termux build: numpy 2.5.4" in capsys.readouterr().out

    result.stdout += dependency_error + "\n"
    assert checker.check_packages() == 1
    assert dependency_error in capsys.readouterr().out

    result.stdout = "another-wheel 1 is not supported on this platform\n"
    assert checker.check_packages() == 1



def test_platform_notice_can_use_stderr_and_distribution_casing(monkeypatch, capsys):
    monkeypatch.setattr(
        checker,
        "native_platform_notices",
        lambda: {"pillow 13.0.0 is not supported on this platform"},
    )
    result = subprocess.CompletedProcess(
        [], 1, "", "Pillow 13.0.0 is not supported on this platform\n"
    )
    monkeypatch.setattr(checker.subprocess, "run", lambda *_args, **_kwargs: result)

    assert checker.check_packages() == 0

    result.stderr += "Unexpected pip error\n"
    assert checker.check_packages() == 1
    assert "Unexpected pip error" in capsys.readouterr().err
