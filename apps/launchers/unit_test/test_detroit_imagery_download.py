"""Explicit source selection and offline-pack provenance without live downloads."""

import io
import json
from unittest.mock import Mock

import pytest

from development.maps import download_detroit_imagery as downloader
from apps.launchers.local_imagery_pack import LocalImageryPack


@pytest.mark.parametrize("coverage,title", [("detroit-downtown","Detroit"),("pine-knob","Pine Knob")])
def test_export_locks_newest_naip_sources_and_retains_provenance(tmp_path, monkeypatch, coverage, title):
    records = [
        {"attributes":{"OBJECTID":1,"Name":"m_4208307_sw_16_2020","Year":2020}},
        {"attributes":{"OBJECTID":2,"Name":"m_4208307_sw_16_2022","Year":2022}},
        {"attributes":{"OBJECTID":3,"Name":"m_partner","Year":2024}},
    ]
    west,south,east,north = downloader.PRESETS[coverage][1]
    export = {"href":"https://imagery.nationalmap.gov/export/example.jpg", "width":2048,"height":1536,
              "extent":{"xmin":west,"ymin":south,"xmax":east,"ymax":north,"spatialReference":{"wkid":4326}}}
    service = Mock(side_effect=[{"serviceDescription":"public domain imagery"}, {"features":records}, export])
    monkeypatch.setattr(downloader,"get_json",service)
    monkeypatch.setattr(downloader.urllib.request,"urlopen",lambda *args, **kwargs: io.BytesIO(b"\xff\xd8fixture"))
    destination = tmp_path / "pack"
    downloader.download(destination, bounds=(west,south,east,north), title=title)
    rule = json.loads(service.call_args.kwargs["mosaicRule"])
    assert rule["lockRasterIds"] == [2]
    document = json.loads((destination / "manifest.json").read_text())
    assert document["source_records"] == [records[1]["attributes"]]
    assert document["title"] == f"{title} NAIP 2022"
    assert (destination / "source-service.json").exists()
    assert LocalImageryPack.load(destination).state.attribution.startswith("USGS / USDA")


def test_missing_naip_does_not_silently_substitute_partner_imagery(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader,"get_json",Mock(side_effect=[
        {"serviceDescription":"public domain imagery"},
        {"features":[{"attributes":{"Name":"other","Year":2024}}]},
    ]))
    with pytest.raises(RuntimeError,match="No identifiable"):
        downloader.download(tmp_path / "pack")
    assert not (tmp_path / "pack").exists()


def test_source_rights_change_stops_download(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader,"get_json",Mock(return_value={"serviceDescription":"other imagery"}))
    with pytest.raises(RuntimeError,match="rights"):
        downloader.download(tmp_path / "pack")


def test_pine_imagery_is_selected_only_inside_its_coverage(tmp_path, monkeypatch):
    import math
    from apps.launchers import local_imagery_pack as packs
    from ui.navigation import GeoPoint
    from ui.navigation.local_imagery_state import LocalImageryState
    pine = tmp_path/'pine'
    pine.mkdir()
    (pine/'manifest.json').write_text('{}')
    bounds = downloader.PRESETS['pine-knob'][1]
    state = LocalImageryState('Pine Knob', 'USGS', *(math.radians(v) for v in bounds))
    monkeypatch.setattr(packs, 'pine_knob_imagery_directory', lambda: pine)
    monkeypatch.setattr(packs, 'detroit_pack_directory', lambda: tmp_path/'detroit')
    monkeypatch.setattr(packs.LocalImageryPack, 'load', lambda directory: Mock(state=state))
    assert packs.preferred_imagery_directory(GeoPoint(math.radians(42.75),math.radians(-83.38))) == pine
    assert packs.preferred_imagery_directory(GeoPoint(math.radians(42.33),math.radians(-83.04))) == tmp_path/'detroit'


def test_imagery_retries_server_errors_without_leaving_a_partial_pack(monkeypatch):
    from urllib.error import HTTPError
    call = Mock(side_effect=HTTPError(downloader.SERVICE,500,'Server error',{},None))
    monkeypatch.setattr(downloader.urllib.request, 'urlopen', call)
    monkeypatch.setattr(downloader.time, 'sleep', lambda seconds: None)
    with pytest.raises(HTTPError):
        downloader.open_source(downloader.SERVICE, timeout=60)
    assert call.call_count == 3


def test_catalog_network_failure_identifies_stage_and_endpoint(monkeypatch):
    from urllib.error import HTTPError
    monkeypatch.setattr(downloader, 'open_source', Mock(side_effect=HTTPError(downloader.SERVICE,502,'Bad Gateway',{},None)))
    with pytest.raises(RuntimeError, match='NAIP source catalog failed after retries') as error:
        downloader.get_json('/query', where="State='MI'")
    assert downloader.SERVICE+'/query' in str(error.value)
