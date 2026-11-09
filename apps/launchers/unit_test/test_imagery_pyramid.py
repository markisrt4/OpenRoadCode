"""Offline zoom addressing, archive activation, request isolation and source audit."""

from io import BytesIO
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import urllib.error
import urllib.request

from PIL import Image
import pytest

from apps.launchers.local_imagery_pyramid import LocalImageryPyramidPack, PILOT_BOUNDS
from apps.launchers.unit_test.test_cesium_viewer import server, state
from development.maps.build_imagery_detail import package, raster_to_pyramid
from development.maps.install_imagery_detail import install
from development.maps.static_tile_trial import digest, write_json, command


@pytest.fixture
def pyramid(tmp_path):
    root=tmp_path/'pyramid';root.mkdir()
    database=root/'imagery.mbtiles'
    image=BytesIO()
    Image.new('RGBA',(256,256),(20,100,80,255)).save(image,format='PNG')
    with sqlite3.connect(database) as connection:
        connection.executescript('CREATE TABLE metadata(name TEXT,value TEXT);'
            'CREATE TABLE tiles(zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB);')
        connection.executemany('INSERT INTO metadata VALUES(?,?)',
            [('minzoom','10'),('maxzoom','10'),('format','png')])
        connection.execute('INSERT INTO tiles VALUES(?,?,?,?)',(10,275,643,image.getvalue()))
    write_json(root/'manifest.json',dict(schema=1,kind='imagery-pyramid',database='imagery.mbtiles',
        title='Test detail',attribution='USDA NAIP',bounds_deg=PILOT_BOUNDS['auburn-hills'],sha256=digest(database)))
    return root


def test_xyz_rows_convert_to_mbtiles_tms_and_missing_tiles_stay_missing(pyramid):
    pack=LocalImageryPyramidPack.load(pyramid)
    assert pack.tile(10,275,380).startswith(b'\x89PNG')
    assert pack.tile(10,276,380) is None
    assert pack.tile(9,1,1) is None
    for address in ((17,1,1),(10,-1,1),(10,1024,1),(10,1,1024)):
        with pytest.raises(ValueError,match='address'):pack.tile(*address)


def test_checksum_is_checked_before_mounting_database(pyramid):
    with (pyramid/'imagery.mbtiles').open('ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='checksum'):
        LocalImageryPyramidPack.load(pyramid)


def test_server_serves_only_bounded_xyz_images_and_transparent_missing_coverage(server,pyramid):
    server._imagery_pyramids=(LocalImageryPyramidPack.load(pyramid),)
    with urllib.request.urlopen(server.url+'config.json') as response:
        layer=json.load(response)['imagery_pyramids'][0]
    assert layer['url']=='/data/imagery-detail/0/{z}/{x}/{y}'
    assert 'database' not in layer and 'sha256' not in layer
    with urllib.request.urlopen(server.url+'data/imagery-detail/0/10/275/380') as response:
        assert response.headers['Content-Type']=='image/png'
        assert Image.open(BytesIO(response.read())).size==(256,256)
    with urllib.request.urlopen(server.url+'data/imagery-detail/0/10/276/380') as response:
        with Image.open(BytesIO(response.read())) as image:
            assert image.convert('RGBA').getpixel((0,0))[3]==0
    for path in ('0/17/1/1','0/10/1024/1','1/10/275/380','0/10/../380'):
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(server.url+'data/imagery-detail/'+path)
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(server.url+'data/imagery-detail/imagery.mbtiles')


def test_detail_installer_keeps_previous_revision_on_invalid_archive(pyramid,tmp_path):
    archive=package(pyramid,tmp_path,'auburn-hills')
    path=tmp_path/archive['archive']
    active=tmp_path/'installed'
    install(path,'auburn-hills',destination=active)
    previous=active.resolve()
    assert LocalImageryPyramidPack.load(active).state.maximum_zoom==10
    with path.open('ab') as stream:stream.write(b'bad')
    with pytest.raises(ValueError):install(path,'auburn-hills',destination=active)
    assert active.resolve()==previous


def test_gdal_produces_native_zoom_tiles_readable_by_runtime(tmp_path):
    if not shutil.which('gdal_create'):
        pytest.skip('GDAL only required on build host')
    coverage='detroit-midtown'
    west,south,east,north=PILOT_BOUNDS[coverage]
    source=tmp_path/'source.tif'
    command('gdal_create','-of','GTiff','-outsize',32,32,'-bands',4,
        '-burn',80,'-burn',120,'-burn',160,'-burn',255,
        '-a_srs','EPSG:4326','-a_ullr',west,north,east,south,source)
    root,report=raster_to_pyramid([source],tmp_path,coverage)
    pack=LocalImageryPyramidPack.load(root)
    assert 10 <= pack.state.minimum_zoom <= 16
    assert pack.state.maximum_zoom==16
    assert report['tile_count']>1
    assert 1 < report['target_ground_pixel_spacing_m'] < 2
    assert report['image_format']=='webp'


def test_complex_campus_and_missing_heights_have_distinct_explanations():
    from development.maps.audit_building_site import classify
    ring=[[-83.23,42.65],[-83.229,42.65],[-83.229,42.651],[-83.23,42.65]]
    feature=dict(id='w1',properties={'building':'yes'},geometry={'type':'Polygon','coordinates':[ring]})
    assert 'placeholder hidden' in classify(feature)['reason']
    feature['properties']['height']='50'
    assert 'height-informed' in classify(feature)['reason']
    feature['geometry']['coordinates'].append(ring)
    assert 'complex footprint' in classify(feature)['reason']
    feature['id']='r1'
    assert 'complex footprint' in classify(feature)['reason']
    feature['geometry']['coordinates'].pop()
    assert 'height-informed' in classify(feature)['reason']


def test_detail_browser_layers_stay_above_late_overviews_and_cleanup():
    node=shutil.which('node')
    if node is None:pytest.skip('Node required for browser controller regression')
    path=Path(__file__).resolve().parents[3]/'frontends/web/cesium/unit_test/test_local_imagery_pyramids.js'
    result=subprocess.run([node,'--test',str(path)],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
