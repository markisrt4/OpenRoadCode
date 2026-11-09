"""Dependency failures must be diagnosed before importing application composition."""

from types import SimpleNamespace
from unittest.mock import Mock
import builtins

import pytest

from apps.orcUi import __main__ as entry


@pytest.mark.parametrize('error',[
    ModuleNotFoundError("No module named 'musicforge'",name='musicforge'),
    ModuleNotFoundError("No module named 'numpy'",name='numpy'),
    OSError('native analysis dependency unavailable'),
])
def test_dependency_failure_exits_with_recovery_before_application_import(monkeypatch,capsys,error):
    monkeypatch.setenv('DISPLAY',':1')
    monkeypatch.setattr(entry.sys,'argv',['runOrcUi'])
    monkeypatch.setattr(entry.sys,'executable','/tmp/ORC environment/bin/python')
    monkeypatch.setattr(entry,'import_module',Mock(side_effect=error))
    original_import=builtins.__import__
    def guarded_import(name,*args,**kwargs):
        if name=='apps.orcUi.main':
            raise AssertionError('Application imported before dependency check')
        return original_import(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guarded_import)
    with pytest.raises(SystemExit) as stopped:entry._main()
    assert stopped.value.code==2
    message=capsys.readouterr().err
    assert 'libMusicForge audio analysis is unavailable' in message
    assert "PYTHON='/tmp/ORC environment/bin/python' bash scripts/installers/install_libmusicforge.sh" in message
    assert str(error) in message
    assert 'Traceback' not in message


def test_incompatible_analysis_api_is_reported_as_dependency_problem(monkeypatch,capsys):
    monkeypatch.setattr(entry,'import_module',lambda name:SimpleNamespace(MusicAnalyzer=object()))
    with pytest.raises(SystemExit):entry._require_musicforge()
    assert 'MusicAnalyzerIf' in capsys.readouterr().err


def test_complete_analysis_api_allows_startup(monkeypatch):
    analysis=SimpleNamespace(**{name:object() for name in
        ('MusicAnalyzer','MusicAnalyzerIf','MusicAnalysisState','PercussionActivity')})
    loader=Mock(return_value=analysis)
    monkeypatch.setattr(entry,'import_module',loader)
    entry._require_musicforge()
    loader.assert_called_once_with('musicforge.analysis')


def test_help_remains_available_without_musicforge(monkeypatch,capsys):
    monkeypatch.setenv('DISPLAY',':1')
    monkeypatch.setattr(entry.sys,'argv',['runOrcUi','--help'])
    check=Mock(side_effect=AssertionError('Help should not load audio analysis'))
    monkeypatch.setattr(entry,'_require_musicforge',check)
    with pytest.raises(SystemExit) as stopped:entry._main()
    assert stopped.value.code==0
    assert 'usage:' in capsys.readouterr().out
    check.assert_not_called()


def test_musicforge_installer_uses_explicit_python_without_running_real_pip(tmp_path):
    from pathlib import Path
    import os
    import subprocess
    interpreter=tmp_path/'selected python'
    calls=tmp_path/'calls.txt'
    interpreter.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$ORC_PYTHON_CALLS"\n')
    interpreter.chmod(0o755)
    script=Path(__file__).resolve().parents[3]/'scripts/installers/install_libmusicforge.sh'
    result=subprocess.run(['bash',str(script)],capture_output=True,text=True,timeout=10,
        env={**os.environ,'PYTHON':str(interpreter),'ORC_PYTHON_CALLS':str(calls),
             'LIBMUSICFORGE_SOURCE':'git+https://example.invalid/fixture.git','PREFIX':''})
    assert result.returncode==0,result.stdout+result.stderr
    recorded=calls.read_text()
    assert '-m pip install' in recorded
    assert 'musicforge.analysis import MusicAnalyzer' in recorded
