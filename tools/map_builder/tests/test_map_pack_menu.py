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
    from development.maps import prebuilt_imagery
    from tools.map_builder.builder.map_pack_selection import Selection
    monkeypatch.setattr(prebuilt_imagery, 'github_release_descriptor',
                        lambda _: 'https://github.com/markisrt4/OpenRoadCode/releases/download/tag/metro-detroit-imagery.zip.json')
    monkeypatch.setattr(prebuilt_imagery, 'read_descriptor',
                        lambda *args: ({'kind': 'terrain', 'bytes': 1048576}, 'unused'))
    monkeypatch.setattr('builtins.input', lambda _: 'y')
    run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(menu.subprocess, 'run', run)
    menu.install_published([Selection('metro-detroit', 1)])
    command = run.call_args.args[0]
    assert command[:3] == [menu.sys.executable, '-m', 'development.maps.install_terrain']
    assert command[-1].endswith('/metro-detroit-terrain.zip.json')
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


def test_nationwide_state_and_region_are_additive():
    from tools.map_builder.builder.map_pack_selection import Selection, effective_selection
    choices = [Selection('us', 1), Selection('mi', 0), Selection('metro-detroit', 4),
               Selection('auburn-hills', 3), Selection('metro-detroit', 4)]
    assert len(effective_selection(choices)) == 4


def test_metro_children_not_top_level_regions():
    from tools.map_builder.builder.map_pack_selection import MICHIGAN_AREAS, METRO_AREAS
    assert 'metro-detroit' in MICHIGAN_AREAS
    assert set(MICHIGAN_AREAS).isdisjoint(METRO_AREAS)
    assert 'southfield' in METRO_AREAS
    assert 'auburn-hills' in METRO_AREAS


def test_basket_survives_returning_between_areas(monkeypatch):
    answers = iter(['1', 'y', '2', '1', '1', '', '', '4', '', ''])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    from tools.map_builder.builder.map_pack_selection import Selection
    review = Mock()
    monkeypatch.setattr(menu, 'review', review)
    assert menu.main() == 0
    assert review.call_args.args[0] == {Selection('us', 1), Selection('mi', 0)}


def test_unavailable_selection_never_starts_build(monkeypatch):
    from tools.map_builder.builder.map_pack_selection import Selection
    run = Mock()
    monkeypatch.setattr(menu.subprocess, 'run', run)
    menu.install_published([Selection('us', 1)])
    run.assert_not_called()
