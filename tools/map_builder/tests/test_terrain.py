import json
from types import SimpleNamespace

import pytest

from tools.map_builder.builder import terrain, map_3d
from tools.map_builder.builder.install_3d import validate_selection
from apps.launchers.local_terrain_pack import load_terrain


def service(monkeypatch, *, missing=False, mixed=False):
    def request(endpoint, parameters):
        if not endpoint:
            return {'pixelType':'F32','serviceDataType':'esriImageServiceDataTypeElevation'}
        points = json.loads(parameters['geometry'])['points']
        samples = [{'location':{'x':x,'y':y}, 'value':180+(y-42.315)*100,
                    'attributes':{'VerticalDatum':'NAVD88'}} for x,y in points]
        if missing:
            samples.pop()
        if mixed:
            samples[0]['attributes']['VerticalDatum'] = 'Other datum'
        return {'samples':samples}
    monkeypatch.setattr(terrain, 'request', request)


def test_midtown_terrain_build_is_runtime_and_deployment_compatible(tmp_path, monkeypatch):
    service(monkeypatch)
    root = tmp_path/'maps/3d/packs/detroit-midtown-terrain'
    terrain.download(root, 'detroit-midtown')
    state = load_terrain(root)
    assert state.width == state.height == 65
    assert state.heights_m[0] > state.heights_m[-1]  # north-first grid
    assert state.vertical_datum == 'NAVD88'
    record = map_3d.validate_pack(root)
    assert record['layers'] == ['terrain'] and record['buildings'] == 0
    assert 'source-samples.json' in record['checksums']
    manifest = {'map_3d':{'detroit-midtown-terrain':record}}
    (tmp_path/'build-manifest.json').write_text(json.dumps(manifest))
    validate_selection(tmp_path, ['detroit-midtown-terrain'])
    (root/'terrain.json').write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        map_3d.validate_pack(root)


@pytest.mark.parametrize('problem', ['missing','mixed'])
def test_incomplete_or_mixed_datum_download_never_installs(tmp_path, monkeypatch, problem):
    service(monkeypatch, **{problem:True})
    destination = tmp_path/'terrain'
    with pytest.raises(RuntimeError):
        terrain.download(destination, 'detroit-midtown')
    assert not destination.exists()


def test_runtime_prefers_deployed_midtown_terrain(tmp_path, monkeypatch):
    from apps.launchers import local_terrain_pack, local_map_tiles_pack
    service(monkeypatch)
    root = tmp_path/'maps/3d/packs/detroit-midtown-terrain'
    terrain.download(root, 'detroit-midtown')
    monkeypatch.setattr(local_terrain_pack,'navigation_data_root',lambda:tmp_path)
    monkeypatch.setattr(local_map_tiles_pack,'navigation_data_root',lambda:tmp_path)
    assert local_terrain_pack.preferred_terrain_directory() == root
    assert local_map_tiles_pack.preferred_tiles_directory() != root


def test_cli_certifies_terrain_and_reuses_it_without_downloading_again(tmp_path, monkeypatch):
    from tools.map_builder.builder import cli
    service(monkeypatch)
    monkeypatch.setattr(cli,'OUTPUT_ROOT',tmp_path)
    monkeypatch.setattr(cli,'parse_args',lambda:SimpleNamespace(command='3d',coverage='detroit-midtown',layer='terrain',yes=True))
    monkeypatch.setattr(cli,'validate_output',lambda root,**kwargs:{'map_3d':map_3d.validate_packs(root)})
    certificate = tmp_path/'build-manifest.json'
    certificate.write_text(json.dumps({'schema':2,'generated_unix':1}))
    assert cli.main() == 0
    manifest = json.loads(certificate.read_text())
    assert manifest['map_3d']['detroit-midtown-terrain']['layers'] == ['terrain']
    original = certificate.read_bytes()
    monkeypatch.setattr(terrain,'request',lambda *args:pytest.fail('certified pack must be reused'))
    assert cli.main() == 0
    assert certificate.read_bytes() == original


def test_cli_download_failure_restores_original_dataset_certificate(tmp_path, monkeypatch):
    from tools.map_builder.builder import cli
    monkeypatch.setattr(cli,'OUTPUT_ROOT',tmp_path)
    monkeypatch.setattr(cli,'parse_args',lambda:SimpleNamespace(command='3d',coverage='detroit-midtown',layer='terrain',yes=True))
    monkeypatch.setattr(cli,'validate_output',lambda root,**kwargs:{'map_3d':map_3d.validate_packs(root)})
    def failed(*args):
        raise RuntimeError('USGS unavailable')
    monkeypatch.setattr(terrain,'request',failed)
    certificate = tmp_path/'build-manifest.json'
    original = b'{"schema":2,"generated_unix":1}'
    certificate.write_bytes(original)
    assert cli.main() != 0
    assert certificate.read_bytes() == original
    assert not (tmp_path/'maps/3d/packs/detroit-midtown-terrain').exists()


def test_direct_device_install_downloads_and_viewer_discovers_local_midtown(tmp_path, monkeypatch):
    from development.maps import install_terrain
    from apps.launchers import local_terrain_pack
    service(monkeypatch)
    destination = tmp_path/'device/map-packs/detroit-midtown-terrain-v1'
    monkeypatch.setattr(install_terrain,'midtown_terrain_directory',lambda:destination)
    monkeypatch.setattr(local_terrain_pack,'midtown_terrain_directory',lambda:destination)
    monkeypatch.setattr(local_terrain_pack,'navigation_data_root',lambda:tmp_path/'absent-dataset')
    monkeypatch.setattr('sys.argv',['install_terrain','--coverage','detroit-midtown','--yes'])
    assert install_terrain.main() == 0
    assert local_terrain_pack.preferred_terrain_directory() == destination
    assert load_terrain(destination).width == 65
    monkeypatch.setattr(terrain,'request',lambda *args:pytest.fail('installed pack must be reused'))
    assert install_terrain.main() == 0


def test_direct_install_cancellation_does_not_download_or_modify_data(tmp_path, monkeypatch):
    from development.maps import install_terrain
    monkeypatch.setattr('sys.argv',['install_terrain','--coverage','detroit-midtown','--output',str(tmp_path/'pack')])
    monkeypatch.setattr('builtins.input',lambda prompt:'n')
    monkeypatch.setattr(install_terrain,'download',lambda *args:pytest.fail('cancelled install must not download'))
    assert install_terrain.main() == 0
    assert not (tmp_path/'pack').exists()


def test_image_service_token_error_uses_public_epqs_with_coarser_grid(tmp_path, monkeypatch):
    def rejected(*args):
        raise terrain.ElevationServiceError({'code':498,'message':'Invalid Token'})
    monkeypatch.setattr(terrain,'request',rejected)
    monkeypatch.setattr(terrain,'_epqs_point',lambda x,y:(180+(y-42.315)*100,
        {'location':{'x':x,'y':y},'value':180+(y-42.315)*100}))
    destination = tmp_path/'terrain'
    terrain.download(destination,'detroit-midtown')
    state = load_terrain(destination)
    assert state.width == state.height == 33
    assert state.heights_m[0] > state.heights_m[-1]
    manifest = json.loads((destination/'manifest.json').read_text())
    assert manifest['source'] == terrain.EPQS
    assert 'EPQS point samples' in manifest['sampling']
    assert 'not specified' in state.vertical_datum
    assert map_3d.validate_pack(destination)['layers'] == ['terrain']


def test_epqs_no_data_does_not_install_partial_pack(tmp_path, monkeypatch):
    def rejected(*args):
        raise terrain.ElevationServiceError({'code':498})
    def no_data(*args):
        raise RuntimeError('EPQS returned no-data')
    monkeypatch.setattr(terrain,'request',rejected)
    monkeypatch.setattr(terrain,'_epqs_point',no_data)
    with pytest.raises(RuntimeError,match='no-data'):
        terrain.download(tmp_path/'terrain','detroit-midtown')
    assert not (tmp_path/'terrain').exists()


def test_epqs_query_requests_metres_and_validates_coordinates(monkeypatch):
    from urllib.parse import urlsplit,parse_qs
    def reply(url):
        assert parse_qs(urlsplit(url).query)['units'] == ['Meters']
        return {'location':{'x':-83.05,'y':42.33},'value':'181.2'}
    monkeypatch.setattr(terrain,'_json_request',reply)
    assert terrain._epqs_point(-83.05,42.33)[0] == 181.2
    with pytest.raises(RuntimeError,match='coordinates'):
        terrain._epqs_point(-83.06,42.33)
