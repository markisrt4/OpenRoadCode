"""Pack entry must never accidentally request source builds or bypass installers."""
from unittest.mock import Mock

import pytest

from tools.map_builder.builder import map_pack_menu as menu


def test_dispatch_uses_selected_request():
    from tools.map_builder.builder.map_pack_builds import BuildRequest
    command = menu.build_command(BuildRequest('metro-detroit-buildings'), 'navigation-cesium')
    assert 'build_target=metro-detroit-buildings' in command
    assert command[command.index('--ref') + 1] == 'navigation-cesium'


def test_cancel_does_not_spawn_process(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: 'b')
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
    from tools.map_builder.builder.map_pack_selection import Selection
    monkeypatch.setattr('builtins.input', lambda _: 'n')
    run = Mock()
    monkeypatch.setattr(menu.subprocess, 'run', run)
    assert menu.request_build({Selection('metro-detroit', 2)}) == 0
    run.assert_not_called()


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
    answers = iter(['1', 'y', '2', '1', '1', '', 'b', '4', 'b', 'b'])
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


def test_build_plan_matches_layers_and_deduplicates():
    from tools.map_builder.builder.map_pack_builds import plan_builds
    from tools.map_builder.builder.map_pack_selection import Selection
    requests, unsupported = plan_builds({Selection('mi', 2), Selection('metro-detroit', 2),
                                         Selection('auburn-hills', 3), Selection('us', 1)})
    assert len(requests) == 4  # statewide buildings, US baseline, two local terrain packs
    assert not any(r.target == 'metro-detroit-buildings' for r in requests)
    assert {dict(r.fields).get('detail_layers') for r in requests if r.fields} == {'terrain'}
    assert unsupported == ()


@pytest.mark.parametrize('coverage,layers', [('southfield', 'terrain'), ('auburn-hills', 'roads')])
def test_workflow_rejects_unreviewed_inputs(coverage, layers):
    from tools.map_builder.builder.map_pack_builds import detail_matrix
    with pytest.raises(ValueError):
        detail_matrix('selected-detail', coverage, layers)


def test_single_detail_does_not_expand_to_pilot():
    from tools.map_builder.builder.map_pack_builds import detail_matrix
    assert detail_matrix('selected-detail', 'detroit-midtown', 'imagery') == (
        ['detroit-midtown'], 'imagery', 17)
    assert detail_matrix('michigan-detail-pilot')[0] == ['detroit-midtown', 'auburn-hills', 'rochester']


def test_unsupported_basket_never_requests_build(monkeypatch):
    from tools.map_builder.builder.map_pack_selection import Selection
    run = Mock()
    monkeypatch.setattr(menu.subprocess, 'run', run)
    assert menu.request_build({Selection('southfield', 4)}) == 0
    run.assert_not_called()


def test_check_all_is_idempotent_and_preserves_other_areas(monkeypatch):
    from tools.map_builder.builder.map_pack_selection import Selection, LAYERS
    answers = iter(['6', '6', ''])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    selected = {Selection('us', 1), Selection('metro-detroit', 2)}
    menu.edit_layers(selected, 'metro-detroit', 'Metro Detroit')
    assert selected == {Selection('us', 1)} | {
        Selection('metro-detroit', layer) for layer in range(len(LAYERS))}


def test_clear_all_only_removes_current_area(monkeypatch):
    from tools.map_builder.builder.map_pack_selection import Selection, LAYERS
    answers = iter(['7', ''])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    selected = {Selection('us', 1)} | {
        Selection('metro-detroit', layer) for layer in range(len(LAYERS))}
    menu.edit_layers(selected, 'metro-detroit', 'Metro Detroit')
    assert selected == {Selection('us', 1)}


def test_blank_in_navigation_does_not_cancel(monkeypatch):
    answers = iter(['', '2'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    assert menu.choose('Areas', ['Michigan', 'US']) == 1


def test_enter_confirms_layer_checklist(monkeypatch):
    from tools.map_builder.builder.map_pack_selection import Selection
    answers = iter(['1', ''])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    selected = set()
    menu.edit_layers(selected, 'mi', 'Michigan')
    assert selected == {Selection('mi', 0)}


def test_national_request_includes_all_fifty_states():
    from development.maps.state_map_catalog import catalog_document
    from development.maps.build_us_terrain import definitions
    from tools.map_builder.builder.map_pack_builds import plan_builds
    from tools.map_builder.builder.map_pack_selection import Selection
    requests, unavailable = plan_builds({Selection('us', 1)})
    assert len(requests) == 1 and requests[0].target == 'us-coarse-terrain'
    assert not unavailable
    states = catalog_document()['states']
    assert len(states) == 50
    assert {'AK', 'HI'} <= {state['abbreviation'] for state in states}
    for state in states:
        _, regions = definitions(state['abbreviation'])
        assert regions
        for region in regions:
            west, south, east, north = region['bounds_deg']
            assert -180 <= west < east <= 180
            assert -90 <= south < north <= 90


def test_national_failure_report_is_not_validated(tmp_path, monkeypatch):
    from development.maps import build_us_terrain as builder
    import json
    def fail(*args, **kwargs):
        raise RuntimeError('No source coverage')
    monkeypatch.setattr(builder, 'raster_region', fail)
    with pytest.raises(RuntimeError):
        builder.build('HI', tmp_path/'out', tmp_path/'cache')
    report = json.loads((tmp_path/'out/us-terrain-report.json').read_text())
    assert report['status'] == 'failed'
    assert not list((tmp_path/'out').glob('*.zip'))


def test_national_probe_profile_uses_three_separate_envelopes():
    from development.maps.build_us_terrain import PROBES, PROFILE
    assert set(PROBES) == {'CO', 'AK', 'HI'}
    assert PROFILE == 'us-staged-1arc-coarse-v1'
    for west, south, east, north in PROBES.values():
        assert east-west == 1 and north-south == 1


def test_coarse_discovery_keeps_existing_detail_default():
    from development.maps.static_region_sources import discover_terrain
    calls = []
    def fetch(*args, **kwargs):
        calls.append(kwargs)
        return {'items': [{'boundingBox': {'minX': 0, 'minY': 0, 'maxX': 1, 'maxY': 1},
                           'downloadURL': 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF/current/dem.tif'}], 'total': 1}
    discover_terrain((0, 0, 1, 1), fetch=fetch)
    discover_terrain((0, 0, 1, 1), fetch=fetch, dataset='National Elevation Dataset (NED) 1 arc-second')
    assert '1/3' in calls[0]['datasets']
    assert '1 arc-second' in calls[1]['datasets']
