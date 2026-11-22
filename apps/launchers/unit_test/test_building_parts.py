"""Building parts retain height provenance and never inherit a solid parent roof."""
import io
import json
import math
import shutil
import subprocess
from unittest.mock import Mock

import pytest

from tools.map_builder.builder import map_3d
from tools.map_builder.builder.building_geometry import normalize_components
from tools.map_builder.builder.building_parts import mark_part_outlines
from ui.navigation.local_building_state import LocalBuilding

BOUNDS=(-84,42,-83,43)
OUTER=[[-83.8,42.2],[-83.6,42.2],[-83.6,42.4],[-83.8,42.4],[-83.8,42.2]]
INNER=[[-83.75,42.25],[-83.65,42.25],[-83.65,42.35],[-83.75,42.35],[-83.75,42.25]]


def feature(tags,ring=INNER):
    return dict(id='w10',properties=tags,geometry=dict(type='Polygon',coordinates=[ring]))


def test_parts_have_absolute_top_and_bottom_heights_with_explicit_provenance():
    part=normalize_components(feature({'building:part':'yes','height':'76','min_height':'12'}),BOUNDS)[0]
    assert part['is_part'] and part['source_id']=='way/10#0'
    assert (part['height_m'],part['min_height_m'],part['height_source'])==(76,12,'osm-height')
    assert LocalBuilding.from_document(json.loads(json.dumps(part))).document()==part
    levels=normalize_components(feature({'building:part':'yes','building:levels':'15','building:min_level':'2'}),BOUNDS)[0]
    assert (levels['height_m'],levels['min_height_m'],levels['height_source'])==(45,6,'levels-estimate')


@pytest.mark.parametrize('minimum',['90','nan','-1','garbage'])
def test_invalid_part_bases_do_not_silently_make_solid_roofs(minimum):
    assert normalize_components(feature({'building:part':'yes','height':'76','min_height':minimum}),BOUNDS)==()


def test_parent_outline_is_not_extruded_over_parts_across_tile_boundaries():
    parent=normalize_components(feature({'building':'commercial','height':'76'},OUTER),BOUNDS)[0]
    part=normalize_components(feature({'building:part':'yes','height':'12'}),BOUNDS)[0]
    cells={(0,0):{'parent':parent},(0,1):{'part':part}}
    assert mark_part_outlines(cells)==1
    assert parent['outline_only'] and parent['height_m']==76
    assert not part.get('outline_only')


def test_unrelated_parts_and_courtyard_buildings_do_not_suppress_parent():
    parent=normalize_components(feature({'building':'yes'},OUTER),BOUNDS)[0]
    parent['holes_rad']=normalize_components(feature({'building':'yes'},INNER),BOUNDS)[0]['ring_rad'],
    part=normalize_components(feature({'building:part':'yes','height':'12'}),BOUNDS)[0]
    # A separate building in the open courtyard is not a component of its neighbor.
    smaller=[[x*.1-83.7*.9,y*.1+42.3*.9] for x,y in INNER]
    part['ring_rad']=tuple((math.radians(x),math.radians(y)) for x,y in smaller)
    assert mark_part_outlines({(0,0):{'parent':parent,'part':part}})==0
    assert not parent.get('outline_only')


def test_extracts_parts_and_records_shape_classification(tmp_path,monkeypatch):
    source=tmp_path/'maps/source/source.osm.pbf';source.parent.mkdir(parents=True);source.write_bytes(b'fixture')
    parent=feature({'building':'yes','height':'76'},OUTER);parent['id']='w1'
    part=feature({'building:part':'yes','height':'45','min_height':'6'})
    calls=Mock(return_value=Mock(stdout=''))
    monkeypatch.setattr(map_3d.subprocess,'run',calls)
    process=Mock(stdout=io.StringIO('\n'.join(json.dumps(f) for f in [parent,part])))
    process.wait.return_value=0
    monkeypatch.setattr(map_3d.subprocess,'Popen',Mock(return_value=process))
    monkeypatch.setitem(map_3d.PRESETS,'fixture',('Fixture',BOUNDS))
    pack=map_3d.build_pack(tmp_path,'fixture')
    assert 'wr/building:part' in calls.call_args_list[1].args[0]
    manifest=json.loads((pack/'manifest.json').read_text())
    assert manifest['schema']==3 and manifest['part_components']==1 and manifest['outlines_with_parts']==1
    assert map_3d.validate_pack(pack)['buildings']==2


def test_real_pbf_exports_standalone_parts_alongside_building_outlines(tmp_path,monkeypatch):
    if not shutil.which('osmium'):pytest.skip('OSM build-host dependency')
    source=tmp_path/'maps/source/test.osm.pbf';source.parent.mkdir(parents=True)
    nodes=[];ways=[]
    for index,(ring,tags) in enumerate([(OUTER,{'building':'yes','height':'76'}),
                                       (INNER,{'building:part':'yes','building:levels':'15','min_height':'6'})]):
        ids=[]
        for offset,(lon,lat) in enumerate(ring[:-1]):
            identity=1+index*10+offset;ids.append(identity)
            nodes.append(f'<node id="{identity}" version="1" lat="{lat}" lon="{lon}"/>')
        refs=''.join(f'<nd ref="{n}"/>' for n in ids+[ids[0]])
        metadata=''.join(f'<tag k="{k}" v="{v}"/>' for k,v in tags.items())
        ways.append(f'<way id="{10+index}" version="1">{refs}{metadata}</way>')
    osm=tmp_path/'fixture.osm';osm.write_text('<osm version="0.6">'+''.join(nodes+ways)+'</osm>')
    subprocess.run(['osmium','cat',str(osm),'-o',str(source)],check=True)
    monkeypatch.setitem(map_3d.PRESETS,'fixture',('Fixture',BOUNDS))
    pack=map_3d.build_pack(tmp_path,'fixture')
    manifest=json.loads((pack/'manifest.json').read_text())
    buildings=[b for t in manifest['tiles'] for b in json.loads((pack/t['id']/'buildings.json').read_text())['buildings']]
    assert len(buildings)==2 and manifest['outlines_with_parts']==1
    part=next(b for b in buildings if b.get('is_part'))
    assert (part['height_m'],part['min_height_m'],part['height_source'])==(45,6,'levels-estimate')
