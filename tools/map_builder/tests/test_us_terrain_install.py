import hashlib
import json
import zipfile

import pytest

from apps.launchers.local_us_terrain import CombinedTerrainIndex, NationalTerrainIndex
from development.maps.install_us_terrain import install
from development.maps.state_map_catalog import state_plan


def fixture(tmp_path):
    source = tmp_path/'download'
    source.mkdir()
    region = state_plan('CO')['overview_regions'][0]
    bounds = region['bounds_deg']
    payload = json.dumps(dict(width=2,height=2,heights_m=[100,200,300,400],reference_height_m=100,vertical_datum='source')).encode()
    digest = hashlib.sha256(payload).hexdigest()
    child = dict(schema=1,title='CO',attribution='USGS',bounds_deg=bounds,sha256=digest)
    mosaic = dict(schema=3,layers=['terrain'],title='CO',bounds_deg=bounds,attribution='USGS',maximum_zoom=10,
                  tiles=[dict(id='r0-c0',path='r0-c0',bounds_deg=bounds,sha256=digest)])
    archive = source/'us-co-overview-terrain.zip'
    with zipfile.ZipFile(archive,'w') as zipped:
        zipped.writestr('manifest.json',json.dumps(mosaic))
        zipped.writestr('r0-c0/manifest.json',json.dumps(child))
        zipped.writestr('r0-c0/terrain.json',payload)
    archive.with_suffix('.zip.json').write_text(json.dumps(dict(schema=1,kind='terrain',coverage='us-co-overview',
        archive=archive.name,bounds_deg=bounds,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))
    return source


def test_install_creates_lazy_catalog_and_keeps_active_on_bad_archive(tmp_path):
    source = fixture(tmp_path)
    destination = tmp_path/'managed'
    install(source,destination=destination,allow_partial=True)
    active = (destination/'active').readlink()
    index = NationalTerrainIndex(destination,json.loads((destination/'active/catalog.json').read_text()))
    assert not index.cache
    zoom=8;x=int((-105+180)/360*2**(zoom+1));y=int((90-39)/180*2**zoom)
    assert index.page(zoom,x,y,0)['tiles']
    assert not index.cache  # Metadata requests do not read elevation arrays.
    assert not index.page(0,0,0,0)['tiles']
    key=next(iter(index.rows))
    assert json.loads(index.chunk(key))['heights_m'][0]==100
    assert len(index.cache)==1
    next(source.glob('*.zip')).write_bytes(b'corrupt')
    with pytest.raises(ValueError):
        install(source,destination=destination,allow_partial=True)
    assert (destination/'active').readlink()==active


def test_normal_install_requires_all_48_before_activation(tmp_path):
    source=fixture(tmp_path)
    with pytest.raises(ValueError,match='48'):
        install(source,destination=tmp_path/'managed')
    assert not (tmp_path/'managed/active').exists()


def test_combined_index_preserves_detail_priority_and_rejects_unknown_chunks():
    class Index:
        def page(self,*args):return {'tiles':[dict(id='regional-detail',detail_level=7)]}
    class National:
        def page(self,*args):return {'tiles':[dict(id='national',detail_level=0)]}
    combined=CombinedTerrainIndex(Index(),National())
    assert [row['id'] for row in combined.page(12,0,0,0)['tiles']]==['regional-detail','national']
    with pytest.raises(ValueError):CombinedTerrainIndex(None,National()).chunk('unknown')


def test_identical_retained_download_copies_do_not_block_install(tmp_path):
    import shutil
    source=fixture(tmp_path)
    duplicate=source/'earlier-copy'
    duplicate.mkdir()
    for path in list(source.glob('*.zip*')):
        shutil.copy2(path,duplicate/path.name)
    destination=tmp_path/'managed'
    install(source,destination=destination,allow_partial=True)
    catalog=json.loads((destination/'active/catalog.json').read_text())
    assert len(catalog['tiles'])==1
