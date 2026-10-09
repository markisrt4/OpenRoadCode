"""Explicit source selection and offline-pack provenance without live downloads."""

import io
import json
from unittest.mock import Mock

import pytest

from development.maps import download_detroit_imagery as downloader
from apps.launchers.local_imagery_pack import LocalImageryPack


def test_export_locks_newest_naip_sources_and_retains_provenance(tmp_path, monkeypatch):
    records = [
        {"attributes":{"OBJECTID":1,"Name":"m_4208307_sw_16_2020","Year":2020}},
        {"attributes":{"OBJECTID":2,"Name":"m_4208307_sw_16_2022","Year":2022}},
        {"attributes":{"OBJECTID":3,"Name":"m_partner","Year":2024}},
    ]
    west,south,east,north = downloader.BOUNDS
    export = {"href":"https://imagery.nationalmap.gov/export/example.jpg", "width":2048,"height":1536,
              "extent":{"xmin":west,"ymin":south,"xmax":east,"ymax":north,"spatialReference":{"wkid":4326}}}
    service = Mock(side_effect=[{"serviceDescription":"public domain imagery"}, {"features":records}, export])
    monkeypatch.setattr(downloader,"get_json",service)
    monkeypatch.setattr(downloader.urllib.request,"urlopen",lambda *args, **kwargs: io.BytesIO(b"\xff\xd8fixture"))
    destination = tmp_path / "pack"
    downloader.download(destination)
    rule = json.loads(service.call_args.kwargs["mosaicRule"])
    assert rule["lockRasterIds"] == [2]
    document = json.loads((destination / "manifest.json").read_text())
    assert document["source_records"] == [records[1]["attributes"]]
    assert document["title"] == "Detroit NAIP 2022"
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
