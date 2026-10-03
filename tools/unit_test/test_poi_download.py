import sqlite3
from unittest.mock import patch

import pytest

from controllers.poi.business_provider_catalog import get_business_provider
from controllers.poi.poi_enricher import enrich_poi
from controllers.poi.poi_models import PoiActionKind, PoiCategory
from controllers.poi.poi_search_source_if import PoiSearchBounds, PoiSearchQuery
from controllers.poi.sqlite_poi_search_source import SqlitePoiSearchSource
from tools.poi_download import build_query, install, main


def node(identifier=1, name='Panera Bread'):
    return {'type': 'node', 'id': identifier, 'lat': 42.5, 'lon': -83.0,
            'tags': {'name': name, 'brand': 'Panera Bread', 'amenity': 'restaurant'}}


def test_import_is_searchable_and_enriched_for_order(tmp_path):
    db = tmp_path / 'search.sqlite'
    counts = install({'elements': [node(), {'type': 'way', 'id': 2,
        'center': {'lat': 42.51, 'lon': -83.01},
        'tags': {'name': 'Gas', 'amenity': 'fuel'}}]}, db)
    assert counts == {'food': 1, 'fuel': 1}
    source = SqlitePoiSearchSource(db)
    try:
        pois = source.search(PoiSearchQuery(PoiCategory.FOOD, PoiSearchBounds(42, -84, 43, -82)))
    finally:
        source.close()
    poi = enrich_poi(pois[0])
    assert poi.poi_id == 'osm:node:1'
    assert any(a.kind is PoiActionKind.ORDER and a.provider_id == 'panera' for a in poi.actions)
    assert get_business_provider('panera').android_package == 'com.panera.bread'


def test_updates_merge_preserve_other_regions_and_address_tables(tmp_path):
    db = tmp_path / 'search.sqlite'
    install({'elements': [node()]}, db)
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO street (id,name,latitude,longitude) VALUES ('s','Main',1,2)")
    install({'elements': [node(2, 'Second')]}, db)
    install({'elements': [node(1, 'Updated')]}, db)
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT count(*) FROM poi').fetchone()[0] == 2
        assert c.execute("SELECT name FROM poi WHERE id='osm:node:1'").fetchone()[0] == 'Updated'
        assert c.execute('SELECT name FROM street').fetchone()[0] == 'Main'


@pytest.mark.parametrize('payload', [
    {'remark': 'timed out', 'elements': []}, {'error': 'bad'},
    {'elements': [node(2), {'type': 'node', 'id': 3, 'lat': 100, 'lon': 0}]},
])
def test_failed_import_preserves_existing_database(tmp_path, payload):
    db = tmp_path / 'search.sqlite'
    install({'elements': [node()]}, db)
    original = db.read_bytes()
    with pytest.raises(ValueError):
        install(payload, db)
    assert db.read_bytes() == original
    assert not list(tmp_path.glob('.poi-download-*'))


@pytest.mark.parametrize('coordinates', [(91, 0, 10), (0, 181, 10), (0, 0, 26), (float('nan'), 0, 1)])
def test_query_rejects_invalid_or_unbounded_area(coordinates):
    with pytest.raises(ValueError):
        build_query(*coordinates)


def test_cli_uses_cached_location_and_termux_path(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENROADCODE_DATA_ROOT', str(tmp_path))
    with patch('tools.poi_download.cached_position', return_value=(42.5, -83.0)), \
         patch('tools.poi_download.download', return_value=snapshot([node()])) as download:
        assert main(['--radius-km', '5']) == 0
    assert 'around:5000,42.5000000,-83.0000000' in download.call_args.args[0]
    assert (tmp_path / 'maps/search/openroadcode-search.sqlite').exists()


def test_cli_reads_bridge_without_cached_position(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENROADCODE_DATA_ROOT', str(tmp_path))
    with patch('tools.poi_download.bridge_position', return_value=(42.5, -83.0)), \
         patch('tools.poi_download.cached_position') as cached, \
         patch('tools.poi_download.download', return_value=snapshot([node()])):
        assert main(['--bridge-position']) == 0
    cached.assert_not_called()


@pytest.mark.parametrize('provider,age', [('simulated_drive', 0), ('gps', 120001)])
def test_bridge_rejects_simulated_or_stale_location(provider, age):
    from types import SimpleNamespace
    from tools.poi_download import bridge_position
    with patch('hardware_io.android.sensor_bridge_client.AndroidSensorBridgeClient') as client:
        client.return_value.read_location.return_value = SimpleNamespace(
            provider=provider, age_ms=age, latitude_deg=42.5, longitude_deg=-83.0,
        )
        with pytest.raises(ValueError):
            bridge_position()


def snapshot(elements):
    return {'version': 0.6, 'osm3s': {'timestamp_osm_base': '2026-10-03T00:00:00Z'},
            'elements': elements}


def test_refresh_removes_deleted_and_reclassified_places_preserving_outside_and_custom(tmp_path):
    db = tmp_path / 'search.sqlite'
    outside = {**node(3), 'lat': 43.0}
    corner = {**node(4), 'lat': 42.58, 'lon': -82.9}
    install({'elements': [node(1), node(2), outside, corner]}, db)
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO poi (id,name,latitude,longitude,category) VALUES ('custom:1','Mine',42.5,-83,'food')")
        c.execute("INSERT INTO street (id,name,latitude,longitude) VALUES ('s','Main',42.5,-83)")
    changed = node(2, 'Now an office')
    changed['tags']['amenity'] = 'office'
    install(snapshot([changed, node(5)]), db, refresh_area=(42.5, -83, 10))
    with sqlite3.connect(db) as c:
        ids = {r[0] for r in c.execute('SELECT id FROM poi')}
        assert ids == {'osm:node:3', 'osm:node:4', 'osm:node:5', 'custom:1'}
        assert c.execute('SELECT name FROM street').fetchone()[0] == 'Main'


def test_complete_empty_snapshot_clears_only_downloaded_area(tmp_path):
    db = tmp_path / 'search.sqlite'
    install({'elements': [node(), {**node(2), 'lat': 43.0}]}, db)
    install(snapshot([]), db, refresh_area=(42.5, -83, 10))
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT id FROM poi').fetchall() == [('osm:node:2',)]


@pytest.mark.parametrize('payload', [
    {'elements': []}, {**snapshot([]), 'remark': 'timeout'},
    snapshot([{'type': 'way', 'id': 2, 'tags': {'name': 'No geometry'}}]),
    snapshot([node(2), {**node(3), 'lat': 100}]),
])
def test_invalid_snapshot_leaves_live_index_unchanged(tmp_path, payload):
    db = tmp_path / 'search.sqlite'
    install({'elements': [node()]}, db)
    before = db.read_bytes()
    with pytest.raises(ValueError):
        install(payload, db, refresh_area=(42.5, -83, 10))
    assert db.read_bytes() == before
    assert not list(tmp_path.glob('.poi-download-*'))


def test_dateline_refresh_preserves_distant_locations(tmp_path):
    db = tmp_path / 'search.sqlite'
    install({'elements': [{**node(1), 'lat': 0, 'lon': -179.99},
                          {**node(2), 'lat': 0, 'lon': 179.5}]}, db)
    install(snapshot([]), db, refresh_area=(0, 179.99, 10))
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT id FROM poi').fetchall() == [('osm:node:2',)]


@pytest.mark.parametrize('tags,expected', [
    ({'website': 'https://local.example/menu', 'contact:website': 'https://other.example'}, 'https://local.example/menu'),
    ({'contact:website': 'https://local.example'}, 'https://local.example'),
    ({'website': 'javascript:alert(1)', 'contact:website': 'https://local.example'}, 'https://local.example'),
    ({'website': 'file:///etc/passwd'}, None),
    ({'website': 'https://user:password@example.com'}, None),
    ({'website': 'https://example.com:bad'}, None),
])
def test_website_tags_become_actions_after_import(tmp_path, tags, expected):
    db = tmp_path / 'search.sqlite'
    item = node()
    item['tags'].update(tags)
    install({'elements': [item]}, db)
    source = SqlitePoiSearchSource(db)
    try:
        poi = enrich_poi(source.search(PoiSearchQuery(PoiCategory.FOOD, PoiSearchBounds(42, -84, 43, -82)))[0])
    finally:
        source.close()
    assert poi.website == expected
    assert [a.uri for a in poi.actions if a.kind is PoiActionKind.OPEN_WEBSITE] == ([expected] if expected else [])
    assert any(a.kind is PoiActionKind.ORDER for a in poi.actions)


def test_existing_index_migrates_without_losing_old_pois(tmp_path):
    db = tmp_path / 'search.sqlite'
    install({'elements': [node()]}, db)
    with sqlite3.connect(db) as c:
        c.execute('ALTER TABLE poi DROP COLUMN website')
    item = node(2, 'Independent Cafe')
    item['tags']['website'] = 'https://cafe.example'
    install({'elements': [item]}, db)
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT count(*) FROM poi').fetchone()[0] == 2
        assert c.execute("SELECT website FROM poi WHERE id='osm:node:2'").fetchone()[0] == 'https://cafe.example'
