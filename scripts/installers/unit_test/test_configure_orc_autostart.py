# SPDX-License-Identifier: MIT
"""Verify the per-user ORC desktop entry lifecycle."""

from scripts.installers.configure_orc_autostart import configure_autostart


def test_autostart_uses_installed_interpreter_and_can_be_removed(tmp_path):
    entry = tmp_path / "config/autostart/openroadcode-orcui.desktop"
    launcher = tmp_path / "ORC checkout/runOrcUi"
    launcher.parent.mkdir()
    launcher.touch(mode=0o700)
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch(mode=0o700)

    for _ in range(2):
        configure_autostart(entry, enabled=True, launcher=launcher, python=python)
    assert f'Exec="/usr/bin/env" "PYTHON={python}" "{launcher}"' in entry.read_text()

    configure_autostart(entry, enabled=False, launcher=launcher, python=python)
    assert not entry.exists()
