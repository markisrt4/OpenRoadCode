"""Statewide cell ownership, atomic install, lazy adapters and loopback paging."""
from io import BytesIO
import json
import math
from pathlib import Path
import sqlite3
import urllib.request
import zipfile

import pytest
from PIL import Image

from development.maps.statewide_detail_plan import plan,xy,bounds,cell_id,PROFILE,intersects,parse_cell
from development.maps.install_statewide_detail import install
from development.maps.static_tile_trial import digest,write_json
from apps.launchers.local_statewide_detail import StatewideDetailIndex,StatewideImagery,PagedTerrainCatalog
from ui.navigation.local_terrain_state import LocalPagedTerrainState
from apps.launchers.unit_test.test_cesium_viewer import server,state  # noqa: F401


def test_statewide_plan_covers_reviewed_cities_and_stays_within_batch_limits():
    document=plan();keys={c['id'] for c in document['cells']}
    assert len(keys)==len(document['cells']) and len(document['batches'])<=256
    assert all(len(b['cells'])<=3 for b in document['batches'])
    assert cell_id(*xy(-83.05,42.33)) in {c['id'] for c in document['batches'][0]['cells']}
    for lon,lat in [(-83.05,42.33),(-85.67,42.96),(-85.62,44.76),(-87.4,46.54),(-87.61,45.11),(-86.74,41.79)]:
        assert cell_id(*xy(lon,lat)) in keys
    for cell in document['cells']:assert cell['bounds_deg']==bounds(cell['x'],cell['y'])
    with pytest.raises(ValueError):parse_cell('../outside')
    with pytest.raises(ValueError):parse_cell('mi-z10-9999-0')


def test_polygon_selection_does_not_fill_large_lake_or_hole_interior():
    polygon=[[(0,0),(4,0),(4,4),(0,4),(0,0)],[(1,1),(3,1),(3,3),(1,3),(1,1)]]
    assert intersects(polygon,(-1,0,.1,.1))
    assert not intersects(polygon,(1.5,1.5,2,2))
    assert not intersects(polygon,(5,5,6,6))


@pytest.fixture
def cell_archive(tmp_path):
    x,y=xy(-83.05,42.33);key=cell_id(x,y);extent=bounds(x,y)
    pack=tmp_path/'source';pack.mkdir();image=pack/'imagery';image.mkdir()
    payload=BytesIO();Image.new('RGBA',(256,256),(20,120,60,255)).save(payload,format='WEBP')
    db=image/'imagery.mbtiles'
    with sqlite3.connect(db) as connection:
        connection.executescript('CREATE TABLE metadata(name TEXT,value TEXT); CREATE TABLE tiles(zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB);')
        connection.executemany('INSERT INTO metadata VALUES(?,?)',[('minzoom','10'),('maxzoom','16'),('format','webp')])
        connection.executemany('INSERT INTO tiles VALUES(?,?,?,?)',[(10,x,2**10-1-y,payload.getvalue()),
            (16,x*64,2**16-1-y*64,payload.getvalue())])
    write_json(image/'manifest.json',dict(schema=1,kind='imagery-pyramid',database='imagery.mbtiles',title=key,
        attribution='USDA NAIP',bounds_deg=extent,sha256=digest(db)))
    terrain=pack/'terrain';tile=terrain/'r0-c0';tile.mkdir(parents=True)
    write_json(tile/'terrain.json',dict(width=129,height=129,heights_m=[230]*(129**2),reference_height_m=230,vertical_datum='relative source'))
    checksum=digest(tile/'terrain.json')
    write_json(tile/'manifest.json',dict(schema=1,title=key,bounds_deg=extent,attribution='USGS',sha256=checksum))
    write_json(terrain/'manifest.json',dict(schema=3,layers=['terrain'],title=key,attribution='USGS',bounds_deg=extent,
        maximum_zoom=16,tiles=[dict(path='r0-c0',bounds_deg=extent,sha256=checksum,detail_level=5,minimum_zoom=12)]))
    write_json(pack/'manifest.json',dict(schema=1,kind='michigan-detail-cell',id=key,profile=PROFILE,bounds_deg=extent,
        imagery_available=True,terrain_available=True))
    downloads=tmp_path/'downloads';downloads.mkdir();archive=downloads/(key+'.zip')
    with zipfile.ZipFile(archive,'w') as zipped:
        for path in pack.rglob('*'):
            if path.is_file():zipped.write(path,path.relative_to(pack))
    write_json(archive.with_suffix('.zip.json'),dict(schema=1,kind='michigan-detail-cell',coverage=key,profile=PROFILE,
        archive=archive.name,bytes=archive.stat().st_size,sha256=digest(archive)))
    write_json(downloads/'statewide-plan.json',dict(profile=PROFILE,cells=[dict(id=key,bounds_deg=extent)]))
    return downloads,key,x,y


def index_for(downloads,destination):
    install(downloads,destination=destination)
    return StatewideDetailIndex(destination,json.loads((destination/'active/catalog.json').read_text()))


def test_cells_install_atomically_and_imagery_opens_only_on_request(cell_archive,tmp_path):
    downloads,key,x,y=cell_archive;root=tmp_path/'device';index=index_for(downloads,root)
    assert not index._images
    assert StatewideImagery(index).tile(10,x,y).startswith(b'RIFF')
    assert len(index._images)==1
    assert StatewideImagery(index).tile(9,x//2,y//2) is None
    previous=(root/'active').resolve()
    with (downloads/(key+'.zip')).open('ab') as stream:stream.write(b'bad')
    with pytest.raises(ValueError):install(downloads,destination=root)
    assert (root/'active').resolve()==previous


def test_loopback_page_and_chunks_use_si_metadata_and_deny_arbitrary_paths(server,cell_archive,tmp_path):
    downloads,key,_,_=cell_archive;index=index_for(downloads,tmp_path/'device')
    server._terrain=PagedTerrainCatalog(LocalPagedTerrainState((),maximum_zoom=16),(),index)
    # Cesium GeographicTilingScheme has 2^(z+1) longitude cells and 2^z rows.
    lon,lat=-83.05,42.33;z=12;x=int((lon+180)/360*2**(z+1));y=int((90-lat)/180*2**z)
    with urllib.request.urlopen(server.url+f'data/terrain-page/{z}/{x}/{y}') as response:page=json.load(response)
    assert len(page['tiles'])==1
    metadata=page['tiles'][0]
    assert metadata['west_rad']==pytest.approx(math.radians(bounds(*xy(lon,lat))[0]))
    assert 'path' not in metadata
    with urllib.request.urlopen(server.url+metadata['url'].lstrip('/')) as response:
        assert json.load(response)['heights_m'][0]==230
    for address in ('data/terrain-chunk/../manifest.json','data/terrain-page/99/0/0','data/terrain-chunk/'+key+'--99'):
        with pytest.raises(urllib.error.HTTPError):urllib.request.urlopen(server.url+address)


def test_missing_statewide_cells_fail_preflight_without_touching_active(cell_archive,tmp_path):
    downloads,_,_,_=cell_archive
    document=json.loads((downloads/'statewide-plan.json').read_text());x,y=xy(-85.67,42.96)
    document['cells'].append(dict(id=cell_id(x,y),bounds_deg=bounds(x,y)))
    write_json(downloads/'statewide-plan.json',document)
    with pytest.raises(ValueError,match='finish downloads'):install(downloads,destination=tmp_path/'device')
    assert not (tmp_path/'device/active').exists()
    install(downloads,allow_partial=True,destination=tmp_path/'device')


def test_browser_paging_lifecycle():
    import shutil
    import subprocess
    node=shutil.which('node')
    if not node:pytest.skip('Node optional for terrain browser regression')
    script=Path(__file__).resolve().parents[3]/'frontends/web/cesium/unit_test/test_paged_terrain.js'
    result=subprocess.run([node,'--test',str(script)],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr


def test_summary_does_not_call_a_partial_state_complete(cell_archive,tmp_path):
    from development.maps.summarize_statewide_detail import summarize
    downloads,key,_,_=cell_archive
    document=json.loads((downloads/'statewide-plan.json').read_text())
    report=summarize(document,downloads)
    assert report['complete'] and report['cells']==1 and report['archive_bytes']>0
    document['cells'].append({'id':'mi-z10-1-1'})
    report=summarize(document,downloads)
    assert not report['complete'] and report['missing_cells']==['mi-z10-1-1']


def test_terrain_baseline_budget_fits_statewide_overview_regions_and_city_pilots():
    from ui.navigation.local_terrain_state import LocalTerrainCatalogState,LocalTerrainTileIndexState
    from ui.navigation.local_imagery_state import LocalImageryState
    coverage=LocalImageryState('Test','USGS',0,0,.1,.1)
    tiles=tuple(LocalTerrainTileIndexState(str(i),coverage,129,129,0,'relative') for i in range(709))
    assert len(LocalTerrainCatalogState(tiles).tiles)==709
