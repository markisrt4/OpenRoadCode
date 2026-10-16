import io
import json
from unittest.mock import Mock

import pytest

from tools.map_builder.builder import map_3d
from tools.map_builder.builder.install_3d import validate_selection
from tools.map_builder.builder.map_3d_menu import select_install_packs, choose_coverage
from apps.launchers.local_map_tiles_pack import LocalMapTilesPack


def feature():
    return {'id':'w1','properties':{'building':'yes','height':'30'},'geometry':{'type':'Polygon',
        'coordinates':[[[-83.05,42.33],[-83.049,42.33],[-83.049,42.331],[-83.05,42.33]]]}}


@pytest.fixture
def built(tmp_path,monkeypatch):
    root = tmp_path/'dataset'
    source = root/'maps/source/michigan.osm.pbf'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'OSM source fixture')
    run = Mock()
    run.real_run = map_3d.subprocess.run
    run.real_popen = map_3d.subprocess.Popen
    process = Mock(stdout=io.StringIO('\x1e'+json.dumps(feature())+'\n'))
    process.wait.return_value = 0
    monkeypatch.setattr(map_3d.subprocess,'run',run)
    monkeypatch.setattr(map_3d.subprocess,'Popen',Mock(return_value=process))
    path = map_3d.build_pack(root,'detroit-midtown')
    return root,path,run


def test_existing_osm_source_builds_runtime_compatible_pack(built):
    root,path,run = built
    assert run.call_args_list[0].args[0][:2] == ['osmium','extract']
    assert run.call_args_list[1].args[0][:2] == ['osmium','tags-filter']
    validated = map_3d.validate_pack(path)
    assert validated['layers'] == ['buildings']
    assert validated['buildings'] == 1
    pack = LocalMapTilesPack.load(path)
    assert all(tile.imagery_available is False for tile in pack.state.tiles)
    assert pack.state.document()['tiles'][0]['imagery_url'] is None
    manifest = json.loads((path/'manifest.json').read_text())
    assert manifest['sources'][0]['sha256'] == map_3d.digest(root/'maps/source/michigan.osm.pbf')


def test_height_estimates_and_holes_are_explicit():
    f = feature()
    f['properties'] = {'building':'yes','building:levels':'5'}
    b = map_3d.normalize(f,map_3d.PRESETS['detroit-midtown'][1])
    assert (b['height_m'],b['height_source']) == (15,'levels-estimate')
    f['geometry']['coordinates'].append(f['geometry']['coordinates'][0])
    assert map_3d.normalize(f,map_3d.PRESETS['detroit-midtown'][1]) is None


def test_invalid_pack_cannot_be_installed(built):
    root,path,_ = built
    record = map_3d.validate_pack(path)
    (root/'build-manifest.json').write_text(json.dumps({'map_3d':{'detroit-midtown':record}}))
    validate_selection(root,['detroit-midtown'])
    with pytest.raises(ValueError,match='Unexpected'):
        validate_selection(root,[])
    (path/'r0-c0/buildings.json').write_text('{}')
    with pytest.raises(ValueError,match='checksum'):
        validate_selection(root,['detroit-midtown'])


def test_menu_selects_packs_and_cancellation_preserves_install(monkeypatch):
    manifest = {'regions':[{'name':'Michigan'}],'map_3d':{'detroit-midtown':{
        'title':'Detroit','layers':['buildings'],'bytes':1024,'bounds_deg':[0,0,1,1],'buildings':1}}}
    answers = iter(['y','y'])
    monkeypatch.setattr('builtins.input',lambda _:next(answers))
    assert select_install_packs(manifest) == ['detroit-midtown']
    answers = iter(['y','n'])
    assert select_install_packs(manifest) is None
    answers = iter(['bad','2'])
    assert choose_coverage() == 'detroit-midtown'


def test_failed_extraction_never_installs_pack(tmp_path,monkeypatch):
    source=tmp_path/'maps/source/michigan.osm.pbf'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'source')
    monkeypatch.setattr(map_3d.subprocess,'run',Mock())
    process = Mock(stdout=io.StringIO('\x1e'+json.dumps(feature())+'\n'))
    process.wait.return_value = 1
    monkeypatch.setattr(map_3d.subprocess,'Popen',Mock(return_value=process))
    with pytest.raises(RuntimeError,match='export failed'):
        map_3d.build_pack(tmp_path,'detroit-midtown')
    assert not (tmp_path/'maps/3d/packs/detroit-midtown').exists()


def test_stage_keeps_partial_selected_pack_and_removes_deselected(built):
    from tools.map_builder.builder.install_3d import prepare_staging
    root,path,_ = built
    partial = path/'partial.tmp'
    partial.write_bytes(b'partial transfer')
    prepare_staging(root,['detroit-midtown'])
    assert partial.exists()
    prepare_staging(root,[])
    assert not path.exists()


def test_termux_menu_cancels_or_validates_before_activation(built,tmp_path,monkeypatch):
    import os
    from pathlib import Path
    import subprocess
    root,path,run = built
    monkeypatch.setattr(map_3d.subprocess,'run',run.real_run)
    monkeypatch.setattr(map_3d.subprocess,'Popen',run.real_popen)
    search=root/'maps/search/openroadcode-search.sqlite'
    search.parent.mkdir()
    search.write_bytes(b'search fixture')
    (root/'build-manifest.json').write_text(json.dumps({'generated_unix':12345,'regions':[{'name':'Michigan'}],
        'map_3d':{'detroit-midtown':map_3d.validate_pack(path)}}))
    bin_dir=tmp_path/'bin'
    bin_dir.mkdir()
    ssh=bin_dir/'ssh'
    ssh.write_text('#!/usr/bin/env python3\nimport os,pathlib,sys\nsys.stdout.write((pathlib.Path(os.environ["REMOTE_FIXTURE"])/"build-manifest.json").read_text())\n')
    rsync=bin_dir/'rsync'
    rsync.write_text('''#!/usr/bin/env python3
import os,pathlib,shutil,sys
if any(':' in arg for arg in sys.argv[1:]):
    source=pathlib.Path(os.environ['REMOTE_FIXTURE'])
    dest=pathlib.Path(sys.argv[-1])
    selected={a.split('/')[4] for a in sys.argv if a.startswith('--include=/maps/3d/packs/')}
    for item in source.iterdir():
        if item.is_dir(): shutil.copytree(item,dest/item.name,dirs_exist_ok=True)
        else: shutil.copy2(item,dest/item.name)
    packs=dest/'maps/3d/packs'
    for pack in packs.iterdir():
        if pack.name not in selected: shutil.rmtree(pack)
else:
    source=pathlib.Path(sys.argv[-2])
    dest=pathlib.Path(sys.argv[-1])
    shutil.copytree(source,dest,dirs_exist_ok=True)
''')
    ssh.chmod(0o755)
    rsync.chmod(0o755)
    target=tmp_path/'vehicle'
    target.mkdir()
    marker=target/'keep'
    marker.write_text('active')
    sdk=target/'cesium/keep-sdk'
    sdk.parent.mkdir()
    sdk.write_bytes(b'installed SDK')
    project=Path(__file__).resolve().parents[3]
    env={**os.environ,'PATH':str(bin_dir)+os.pathsep+os.environ['PATH'],
         'REMOTE_FIXTURE':str(root),'NAV_DATA_ROOT':str(target)}
    script=project/'development/termux/pull_navigation_data.sh'
    def pull(answers):
        return subprocess.run(['bash',str(script),'--interactive','test-host'],input=answers,
                              capture_output=True,text=True,env=env,timeout=20)
    cancelled=pull('y\nn\n')
    assert cancelled.returncode == 0, cancelled.stderr
    assert marker.exists()
    # Matching source certificate, but a corrupted transferred payload must not replace active data.
    original = (path/'r0-c0/buildings.json').read_bytes()
    (path/'r0-c0/buildings.json').write_bytes(b'corrupt')
    failed=pull('y\ny\n')
    assert failed.returncode != 0
    assert marker.exists()
    assert 'checksum' in failed.stderr

    (path/'r0-c0/buildings.json').write_bytes(original)
    success=pull('y\ny\n')
    assert success.returncode == 0, success.stdout+success.stderr
    assert not marker.exists()
    assert sdk.read_bytes() == b'installed SDK'
    assert (target/'maps/3d/packs/detroit-midtown/manifest.json').exists()


def test_builder_geometry_reuses_matching_cached_imagery(built,tmp_path,monkeypatch):
    import shutil
    from apps.launchers import local_map_tiles_pack as runtime
    root,path,_ = built
    cached=tmp_path/'imagery-cache'
    shutil.copytree(path,cached)
    manifest=json.loads((cached/'manifest.json').read_text())
    for tile in manifest['tiles']:
        image=cached/tile['id']/'imagery.jpg'
        image.write_bytes(b'\xff\xd8fixture')
        tile['sha256']['imagery.jpg']=map_3d.digest(image)
    (cached/'manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(runtime,'detroit_tiles_directory',lambda:cached)
    combined=runtime.load_viewer_tiles(path)
    assert all(tile.imagery_available for tile in combined.state.tiles)
    assert combined.files['r0-c0']['imagery.jpg'].is_relative_to(cached)
    assert combined.files['r0-c0']['buildings.json'].is_relative_to(path)


def test_osmium_single_part_multipolygon_matches_polygon():
    polygon=feature()
    expected=map_3d.normalize(polygon,map_3d.PRESETS['detroit-midtown'][1])
    multi=feature()
    multi['geometry']={'type':'MultiPolygon','coordinates':[multi['geometry']['coordinates']]}
    assert map_3d.normalize(multi,map_3d.PRESETS['detroit-midtown'][1]) == expected
    multi['geometry']['coordinates'].append(multi['geometry']['coordinates'][0])
    assert map_3d.normalize(multi,map_3d.PRESETS['detroit-midtown'][1]) is None
