"""Installed MVT road/name decoding and XYZ-to-TMS lookup without live services."""
import gzip
import math
import sqlite3

import pytest

from apps.launchers.local_road_overlay import LocalRoadOverlay, decode_overlay, geometry_paths


def varint(number):
    data=bytearray()
    while number>127:
        data.append((number&127)|128);number>>=7
    data.append(number)
    return bytes(data)


def field(number,value):
    return varint(number*8+2)+varint(len(value))+value


def layer(name,kind,label,geometry_type,geometry,name_key=None):
    feature=field(2,b'\x00\x00\x01\x01')+varint(3*8)+varint(geometry_type)+field(4,geometry)
    content=field(1,name.encode())+field(2,feature)+field(3,b'class')+field(3,name_key or (b'ref' if name=='transportation_name' else b'name'))
    content+=field(4,field(1,kind.encode()))+field(4,field(1,label.encode()))+varint(5*8)+varint(4096)
    return field(3,content)


def vector_tile():
    move=b''.join(varint(value) for value in (9,4000,4000))
    line=move+b''.join(varint(value) for value in (10,100,100))
    return layer('transportation_name','motorway','I-75',2,line)+layer('place','city','Southfield',1,move)


def test_roads_and_places_decode_with_si_points():
    state=decode_overlay(gzip.compress(vector_tile()),14,4000,5000)
    assert state.roads[0].label=='I-75'
    assert not state.roads[0].geometry_visible
    assert len(state.roads[0].points)==2
    assert state.places[0].name=='Southfield'
    assert all(abs(point.longitude_rad)<=math.pi and abs(point.latitude_rad)<=math.pi/2 for point in state.roads[0].points)


def test_xyz_request_reads_matching_tms_row_and_caches(tmp_path):
    path=tmp_path/'maps.mbtiles'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE tiles (zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB)')
        db.execute('INSERT INTO tiles VALUES (?,?,?,?)',(14,4000,2**14-1-5000,vector_tile()))
    source=LocalRoadOverlay(path)
    state=source.tile(14,4000,5000)
    assert state.places[0].name=='Southfield'
    assert source.tile(14,4000,5000) is state
    assert not source.tile(14,4000,5001).roads
    with pytest.raises(ValueError):source.tile(30,0,0)


def test_invalid_commands_and_unbounded_decompression_are_rejected():
    with pytest.raises(ValueError):geometry_paths(b'\x00')
    with pytest.raises(ValueError):decode_overlay(gzip.compress(b'x'*(8*1024*1024+1)),14,0,0)


def test_metadata_limits_zoom_to_installed_dataset(tmp_path):
    path=tmp_path/'roads.mbtiles'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE metadata (name TEXT,value TEXT)')
        db.execute("INSERT INTO metadata VALUES ('maxzoom','12')")
    assert LocalRoadOverlay(path).max_zoom == 12


def test_local_street_and_city_latin_names_are_read():
    move=b''.join(varint(value) for value in (9,4000,4000))
    line=move+b''.join(varint(value) for value in (10,100,100))
    # Rebuild field lengths when changing the attribute key.
    tile=layer('transportation_name','minor','Main Street',2,line,name_key=b'name:latin')
    city=layer('place','city','Rochester',1,move,name_key=b'name:latin')
    state=decode_overlay(tile+city,14,4000,5000)
    assert state.roads[0].label=='Main Street'
    assert state.places[0].name=='Rochester'
    assert not decode_overlay(tile,12,400,500).roads


def test_transportation_geometry_draws_but_name_placement_path_does_not():
    move=b''.join(varint(value) for value in (9,4000,4000))
    line=move+b''.join(varint(value) for value in (10,100,100))
    tile=(layer('transportation_name','primary','Woodward Avenue',2,line)
          + layer('transportation','primary','Woodward Avenue',2,line))
    state=decode_overlay(tile,13,2000,2500)
    assert [road.geometry_visible for road in state.roads] == [True,False]


def test_overview_city_label_survives_detail_tile_without_places(tmp_path):
    path=tmp_path/'places.mbtiles'
    move=b''.join(varint(value) for value in (9,4000,4000))
    city=layer('place','city','Rochester',1,move,name_key=b'name:latin')
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE tiles (zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB)')
        db.execute('INSERT INTO tiles VALUES (?,?,?,?)',(10,250,1023-312,city))
    # The parent point lies 7 detailed tiles into this zoom-10 tile.
    state=LocalRoadOverlay(path).tile(14,250*16+7,312*16+7)
    assert [place.name for place in state.places]==['Rochester']
    assert not LocalRoadOverlay(path).tile(14,250*16+6,312*16+7).places


def test_place_labels_are_budgeted_and_filtered_by_zoom():
    move=b''.join(varint(value) for value in (9,4000,4000))
    suburbs = b''.join(
        layer('place','suburb',name,1,move) for name in ('One','Two','Three')
    )
    cities = b''.join(
        layer('place','city',name,1,move) for name in ('Detroit','Pontiac','Troy')
    )

    overview = decode_overlay(suburbs + cities, 10, 250, 312)
    detail = decode_overlay(suburbs + cities, 14, 4000, 5000)

    assert [place.name for place in overview.places] == ['Detroit']
    assert [place.name for place in detail.places] == ['Detroit','Pontiac','Troy']
