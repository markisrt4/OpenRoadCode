"""Pack entry must never accidentally request source builds or bypass installers."""
from unittest.mock import Mock

import pytest

from tools.map_builder.builder import map_pack_menu as menu


def test_cloud_request_limits_state_to_overview():
    command = menu.build_command('generic-state', 'navigation-cesium', 'Michigan')
    assert 'state=MI' in command
    assert 'scope=overview' in command
    assert command[command.index('--ref') + 1] == 'navigation-cesium'
    assert 'michigan-statewide-detail' not in command


def test_unreviewed_costly_target_is_rejected():
    with pytest.raises(ValueError):
        menu.build_command('michigan-statewide-detail', 'navigation-cesium')


def test_cancel_does_not_spawn_process(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: '')
    run = Mock()
    monkeypatch.setattr(menu.subprocess, 'run', run)
    assert menu.main() == 0
    run.assert_not_called()


def test_terrain_reuses_verified_installer(monkeypatch):
    answers = iter(['2', 'michigan-overview', 'https://example.org/terrain.zip.json'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(menu.subprocess, 'run', run)
    assert menu.main() == 0
    command = run.call_args.args[0]
    assert command[:3] == [menu.sys.executable, '-m', 'development.maps.install_terrain']
    assert '--pack-manifest' in command
    assert '--yes' not in command


def test_cloud_build_requires_final_confirmation(monkeypatch):
    answers = iter(['1', 'n'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    monkeypatch.setattr(menu.shutil, 'which', lambda _: '/usr/bin/gh')
    run = Mock(return_value=Mock(stdout='navigation-cesium\n'))
    monkeypatch.setattr(menu.subprocess, 'run', run)
    assert menu.request_build() == 0
    assert run.call_count == 1
    assert run.call_args.args[0] == ['git', 'branch', '--show-current']
