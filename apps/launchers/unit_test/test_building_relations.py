"""Bounded relation geometry, legacy reads, and actual Osmium assembly in CI."""
import io
import json
import shutil
import subprocess
from unittest.mock import Mock

import pytest

from ui.navigation.local_building_state import LocalBuilding
from tools.map_builder.builder.building_geometry import normalize_components, outer_members
from tools.map_builder.builder import map_3d

BOUNDS = (-84,42,-83,43)
OUTER = [[-83.8,42.2],[-83.6,42.2],[-83.6,42.4],[-83.8,42.4],[-83.8,42.2]]
HOLE = [[-83.75,42.25],[-83.65,42.25],[-83.65,42.35],[-83.75,42.35],[-83.75,42.25]]


def relation():
    return dict(id='r20',properties={'@type':'relation','@id':20,'building':'yes','height':'76'},
                geometry={'type':'MultiPolygon','coordinates':[[OUTER,HOLE],[OUTER]]})


def test_multipart_courtyard_round_trip_and_legacy_contract():
    components=normalize_components(relation(),BOUNDS)
    assert len(components)==2
    assert [b['source_id'] for b in components]==['relation/20#0','relation/20#1']
    assert len(components[0]['holes_rad'])==1
    for document in components:
        assert LocalBuilding.from_document(json.loads(json.dumps(document))).document()==document
    legacy=LocalBuilding.from_document({k:v for k,v in components[1].items() if k!='source_id'})
    assert legacy.holes==() and legacy.source_id==''
    assert 'holes_rad' not in legacy.document()


@pytest.mark.parametrize('failure',['unclosed','outside','too-many','partial'])
def test_invalid_relation_never_flattens_or_partially_publishes(failure):
    feature=relation()
    if failure=='unclosed':feature['geometry']['coordinates'][0][1]=HOLE[:-1]
    if failure=='outside':feature['geometry']['coordinates'][0][1]=OUTER
    if failure=='too-many':feature['geometry']['coordinates'][0]=[OUTER]+[HOLE]*65
    if failure=='partial':feature['geometry']['coordinates'][1]=[[[-90,0]]]
    assert normalize_components(feature,BOUNDS)==()


def test_membership_parser_keeps_inner_buildings_separate():
    assert outer_members('r20 v1 Mw10@outer,w11@inner,w12@,n5@label\n')=={'relation/20':{'way/10','way/12'}}


@pytest.mark.parametrize('accepted',[True,False])
def test_only_accepted_relations_suppress_matching_member_way(tmp_path,monkeypatch,accepted):
    source=tmp_path/'maps/source/source.osm.pbf'
    source.parent.mkdir(parents=True);source.write_bytes(b'fixture')
    feature=relation();feature['geometry']['coordinates']=[ [OUTER,HOLE] ]
    if not accepted:feature['geometry']['coordinates'][0][1]=HOLE[:-1]
    way=dict(id='w10',properties={'building':'yes','height':'76'},
             geometry={'type':'Polygon','coordinates':[OUTER]})
    monkeypatch.setattr(map_3d.subprocess,'run',Mock(return_value=Mock(stdout='r20 Mw10@outer\n')))
    process=Mock(stdout=io.StringIO('\n'.join(json.dumps(f) for f in [way,feature])))
    process.wait.return_value=0
    monkeypatch.setattr(map_3d.subprocess,'Popen',Mock(return_value=process))
    monkeypatch.setitem(map_3d.PRESETS,'fixture',('Fixture',BOUNDS))
    pack=map_3d.build_pack(tmp_path,'fixture')
    manifest=json.loads((pack/'manifest.json').read_text())
    assert manifest['schema']==2
    assert sum(t['buildings_count'] for t in manifest['tiles'])==1
    assert manifest['duplicate_member_ways_removed']==int(accepted)
    assert manifest['courtyard_components']==int(accepted)


def test_actual_osmium_relation_assembly_packaging_and_activation(tmp_path,monkeypatch):
    if not shutil.which('osmium'):pytest.skip('OSM build-host dependency')
    from tools.map_builder.builder.building_artifact import package
    from development.maps.install_buildings import install
    root=tmp_path/'dataset';source=root/'maps/source/test.osm.pbf'
    source.parent.mkdir(parents=True)
    # Outer way is tagged too; relation must retain its courtyard without a
    # duplicate filled member roof. Disjoint second outer becomes a component.
    rings=[OUTER,HOLE,[[x+.3,y] for x,y in OUTER]]
    nodes=[];ways=[]
    for index,ring in enumerate(rings):
        ids=[]
        for offset,(lon,lat) in enumerate(ring[:-1]):
            identity=1+index*10+offset;ids.append(identity)
            nodes.append(f'<node id="{identity}" version="1" lat="{lat}" lon="{lon}"/>')
        refs=''.join(f'<nd ref="{n}"/>' for n in ids+[ids[0]])
        tags='<tag k="building" v="yes"/><tag k="height" v="76"/>' if index==0 else ''
        ways.append(f'<way id="{10+index}" version="1">{refs}{tags}</way>')
    relation_xml='''<relation id="20" version="1"><member type="way" ref="10" role="outer"/>
<member type="way" ref="11" role="inner"/><member type="way" ref="12" role="outer"/>
<tag k="type" v="multipolygon"/><tag k="building" v="yes"/><tag k="height" v="76"/></relation>'''
    osm=tmp_path/'fixture.osm'
    osm.write_text('<osm version="0.6">'+''.join(nodes+ways)+relation_xml+'</osm>')
    subprocess.run(['osmium','cat',str(osm),'-o',str(source)],check=True)
    monkeypatch.setitem(map_3d.PRESETS,'metro-detroit',('Fixture',BOUNDS))
    pack=map_3d.build_pack(root,'metro-detroit')
    manifest=json.loads((pack/'manifest.json').read_text())
    buildings=[b for t in manifest['tiles'] for b in json.loads((pack/t['id']/'buildings.json').read_text())['buildings']]
    assert len(buildings)==2
    assert all(b['source_id'].startswith('relation/20#') and b['height_m']==76 for b in buildings)
    assert sum(bool(b.get('holes_rad')) for b in buildings)==1
    archive=tmp_path/'buildings.zip'
    package(pack,archive,'metro-detroit')
    # Installer coverage is the production Metro preset; fixture lies within it.
    active=tmp_path/'active'
    monkeypatch.setattr('development.maps.install_buildings.PRESETS',map_3d.PRESETS)
    install(archive,destination=active)
    assert active.is_symlink()
    assert map_3d.validate_pack(active)['buildings']==2
