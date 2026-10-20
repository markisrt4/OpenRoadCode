"""Sample ordering, source heights, and complete-pack installation are explicit."""

import hashlib
import gzip
import json
import math
from unittest.mock import Mock

import pytest

from apps.launchers.local_terrain_pack import load_terrain
from development.maps import download_detroit_terrain as downloader
from tools.map_builder.builder import terrain
from ui.navigation.local_imagery_state import LocalImageryState
from ui.navigation.local_terrain_state import LocalTerrainMosaicState, LocalTerrainState


def test_invalid_or_incomplete_heights_are_rejected():
    coverage = LocalImageryState("terrain","USGS",-.1,.1,.1,.2)
    with pytest.raises(ValueError):
        LocalTerrainState(coverage,2,2,(1,2,3),2,"source")
    with pytest.raises(ValueError):
        LocalTerrainState(coverage,2,2,(1,2,math.nan,4),2,"source")


def test_download_preserves_source_grid_and_reports_relative_display(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader,"SIZE",3)
    def reply(endpoint, parameters):
        if not endpoint:
            return {"pixelType":"F32","serviceDataType":"esriImageServiceDataTypeElevation"}
        points = json.loads(parameters["geometry"])["points"]
        assert json.loads(parameters["renderingRule"])["rasterFunction"] == "None"
        return {"samples":[{"location":{"x":x,"y":y},"value":str(180+i),
                            "attributes":{"VerticalDatum":"NAVD88"}}
                           for i,(x,y) in enumerate(points)]}
    monkeypatch.setattr(terrain,"request",reply)
    destination = tmp_path / "terrain"
    downloader.download(destination)
    state = load_terrain(destination)
    assert state.heights_m == tuple(range(180,189))
    assert state.reference_height_m == 184
    assert state.vertical_datum == "NAVD88"
    assert state.document()["display_mode"] == "relative-relief"
    assert (destination / "source-samples.json.gz").exists()
    responses = json.loads(gzip.decompress((destination / "source-samples.json.gz").read_bytes()))
    assert len(responses[0]["samples"]) == 9
    data = destination / "terrain.json"
    data.write_bytes(data.read_bytes()+b" ")
    with pytest.raises(ValueError,match="checksum"):
        load_terrain(destination)


def test_incomplete_sample_reply_is_not_installed(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader,"SIZE",3)
    monkeypatch.setattr(terrain,"request",Mock(side_effect=[
        {"pixelType":"F32","serviceDataType":"esriImageServiceDataTypeElevation"},
        {"samples":[]},
    ]))
    with pytest.raises(RuntimeError,match="every ground point"):
        downloader.download(tmp_path / "terrain")
    assert not (tmp_path / "terrain").exists()


def _terrain_tile(root, bounds, heights, reference):
    root.mkdir()
    payload = json.dumps({"width": 2, "height": 2, "heights_m": heights,
                          "reference_height_m": reference, "vertical_datum": "NAVD88"})
    (root / "terrain.json").write_text(payload)
    (root / "manifest.json").write_text(json.dumps({
        "schema": 1, "title": root.name, "attribution": "USGS",
        "bounds_deg": bounds,
        "sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }))


def test_mosaic_uses_one_reference_plane_and_validates_child_records(tmp_path):
    root = tmp_path / "mosaic"
    root.mkdir()
    _terrain_tile(root / "west", [-84, 42, -83, 43], [100, 101, 102, 103], 100)
    _terrain_tile(root / "east", [-83, 42, -82, 43], [200, 201, 202, 203], 200)
    records = []
    for name, bounds in (("west", [-84, 42, -83, 43]), ("east", [-83, 42, -82, 43])):
        records.append({"path": name, "bounds_deg": bounds,
                        "sha256": hashlib.sha256((root / name / "terrain.json").read_bytes()).hexdigest()})
    manifest = {"schema": 2, "layers": ["terrain"], "attribution": "USGS", "tiles": records}
    (root / "manifest.json").write_text(json.dumps(manifest))

    state = load_terrain(root)
    assert isinstance(state, LocalTerrainMosaicState)
    assert {tile["reference_height_m"] for tile in state.document()["tiles"]} == {150}

    records[0]["path"] = "../west"
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="inside the pack"):
        load_terrain(root)


def test_lod_mosaic_uses_overview_reference_and_exposes_detail_metadata(tmp_path):
    root = tmp_path / "lod"
    root.mkdir()
    _terrain_tile(root / "overview", [-84, 42, -82, 43], [100, 101, 102, 103], 100)
    _terrain_tile(root / "focus", [-83.1, 42.3, -83.0, 42.4], [200, 201, 202, 203], 200)
    records = []
    for name, bounds, detail, zoom in (
            ("overview", [-84, 42, -82, 43], 0, 0),
            ("focus", [-83.1, 42.3, -83.0, 42.4], 2, 12)):
        records.append({"path": name, "bounds_deg": bounds, "detail_level": detail,
                        "minimum_zoom": zoom,
                        "sha256": hashlib.sha256((root/name/"terrain.json").read_bytes()).hexdigest()})
    (root / "manifest.json").write_text(json.dumps({
        "schema": 3, "layers": ["terrain"], "attribution": "USGS",
        "maximum_zoom": 16, "tiles": records,
    }))
    state = load_terrain(root)
    document = state.document()
    assert document["maximum_zoom"] == 16
    assert {tile["detail_level"] for tile in document["tiles"]} == {0, 2}
    assert {tile["reference_height_m"] for tile in document["tiles"]} == {100}
