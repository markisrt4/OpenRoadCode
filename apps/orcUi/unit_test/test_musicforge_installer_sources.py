"""Source selection must reject old 0.1.0 trees without executing real pip."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def installer(tmp_path):
    project=tmp_path/'workspace/OpenRoadCode'
    directory=project/'scripts/installers'
    directory.mkdir(parents=True)
    original=Path(__file__).resolve().parents[3]/'scripts/installers/install_libmusicforge.sh'
    script=directory/original.name
    shutil.copy2(original,script)
    interpreter=tmp_path/'selected python'
    interpreter.write_text('''#!/bin/sh
if [ "$1" = "-" ]; then
  exec "$ORC_REAL_PYTHON" "$@"
fi
printf '%s\\n' "$*" >> "$ORC_PYTHON_CALLS"
''')
    interpreter.chmod(0o755)
    calls=tmp_path/'calls.txt'
    env={**os.environ,'PYTHON':str(interpreter),'ORC_REAL_PYTHON':sys.executable,
         'ORC_PYTHON_CALLS':str(calls),'PREFIX':''}
    env.pop('LIBMUSICFORGE_SOURCE',None)
    sibling=project.parent/'libMusicForge'
    def run(source=None, termux=False):
        selected=env.copy()
        if source is not None:selected['LIBMUSICFORGE_SOURCE']=str(source)
        if termux:selected['PREFIX']='/data/data/com.termux/files/usr'
        return subprocess.run(['bash',str(script)],env=selected,capture_output=True,text=True,timeout=10)
    return sibling,calls,run


def local_package(root, *, analysis):
    root.mkdir()
    text='[project]\nname="libmusicforge"\nversion="0.1.0"\n'
    if analysis:
        text+='[project.optional-dependencies]\nanalysis=["numpy>=1.26"]\n'
        module=root/'src/musicforge/analysis/__init__.py'
        module.parent.mkdir(parents=True)
        module.write_text('# Compatible source-layout fixture\n')
    (root/'pyproject.toml').write_text(text)


def test_stale_sibling_falls_back_to_verified_remote_without_changing_checkout(installer):
    sibling,calls,run=installer
    local_package(sibling,analysis=False)
    previous=(sibling/'pyproject.toml').read_bytes()
    result=run()
    assert result.returncode==0,result.stderr
    assert 'Skipping incompatible sibling' in result.stderr
    command=calls.read_text()
    assert 'libMusicForge.git@7ca7cd444291ab02bea0e82df13bd05620634420' in command
    forced=[line for line in command.splitlines() if '--force-reinstall' in line]
    assert len(forced)==1 and '--no-deps' in forced[0]
    assert (sibling/'pyproject.toml').read_bytes()==previous


def test_explicit_stale_local_override_fails_before_pip(installer):
    sibling,calls,run=installer
    local_package(sibling,analysis=False)
    result=run(sibling)
    assert result.returncode==1
    assert 'lacks the analysis module or extra' in result.stderr
    assert not calls.exists()


def test_compatible_sibling_still_supports_local_library_development(installer):
    sibling,calls,run=installer
    local_package(sibling,analysis=True)
    result=run()
    assert result.returncode==0,result.stderr
    command=calls.read_text()
    requirement=next(line for line in command.splitlines() if ' --upgrade ' in line).split(' --upgrade ',1)[1]
    assert requirement.endswith('[analysis]')
    assert Path(requirement.removesuffix('[analysis]')).resolve()==sibling.resolve()
    assert 'git+https://' not in command


def test_termux_replaces_package_without_asking_pip_to_install_numpy(installer):
    sibling,calls,run=installer
    local_package(sibling,analysis=False)
    result=run(termux=True)
    assert result.returncode==0,result.stderr
    command=calls.read_text()
    assert '--force-reinstall --no-deps git+https://' in command
    assert '[analysis]' not in command
    assert '-c import numpy' in command
