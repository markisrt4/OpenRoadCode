"""Sample ordering, source heights, and complete-pack installation are explicit."""

import hashlib
import json
import math
from unittest.mock import Mock

import pytest

from apps.launchers.local_terrain_pack import load_terrain
from development.maps import download_detroit_terrain as downloader
from ui.navigation.local_imagery_state import LocalImageryState
from ui.navigation.local_terrain_state import LocalTerrainState


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
    monkeypatch.setattr(downloader,"request",reply)
    destination = tmp_path / "terrain"
    downloader.download(destination)
    state = load_terrain(destination)
    assert state.heights_m == tuple(range(180,189))
    assert state.reference_height_m == 184
    assert state.vertical_datum == "NAVD88"
    assert state.document()["display_mode"] == "relative-relief"
    assert (destination / "source-samples.json").exists()
    data = destination / "terrain.json"
    data.write_bytes(data.read_bytes()+b" ")
    with pytest.raises(ValueError,match="checksum"):
        load_terrain(destination)


def test_incomplete_sample_reply_is_not_installed(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader,"SIZE",3)
    monkeypatch.setattr(downloader,"request",Mock(side_effect=[
        {"pixelType":"F32","serviceDataType":"esriImageServiceDataTypeElevation"},
        {"samples":[]},
    ]))
    with pytest.raises(RuntimeError,match="every ground point"):
        downloader.download(tmp_path / "terrain")
    assert not (tmp_path / "terrain").exists()
