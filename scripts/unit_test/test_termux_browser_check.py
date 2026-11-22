"""The environment check accepts the same browser executables as the launcher."""
import os
from pathlib import Path
import subprocess
import pytest


@pytest.mark.parametrize('browser', ['chromium-browser', 'chromium', 'google-chrome', None])
def test_browser_executable_aliases(tmp_path, browser):
    root=Path(__file__).resolve().parents[2]
    commands=['python','git','termux-x11','xfce4-session','dbus-launch','xrandr','dirname']
    binary=tmp_path/'bin'
    binary.mkdir()
    for name in commands+([browser] if browser else []):
        target=binary/name
        target.write_text('#!/bin/bash\n'+('/usr/bin/dirname "$@"' if name=='dirname' else 'exit 0')+'\n')
        target.chmod(0o755)
    venv=tmp_path/'venv'
    (venv/'bin').mkdir(parents=True)
    (venv/'bin/python').symlink_to(binary/'python')
    result=subprocess.run(['/bin/bash',str(root/'scripts/termux/check_termux.sh'),str(venv),'browser'],
        env={**os.environ,'PATH':str(binary),'PREFIX':'/data/data/com.termux/files/usr'},
        text=True,capture_output=True)
    assert result.returncode==(0 if browser else 1),result.stdout+result.stderr
    assert (browser or 'Browser missing') in result.stdout+result.stderr
