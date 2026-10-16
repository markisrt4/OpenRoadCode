"""Validate a local building pack before exposing its presentation snapshot."""
import hashlib
import json
from pathlib import Path

from common.xdg_paths import openroadcode_data_dir
from ui.navigation.local_building_state import LocalBuilding, LocalBuildingState


def detroit_building_directory():
    return openroadcode_data_dir("map-packs", "detroit-buildings-v1")


def load_buildings(directory):
    root = Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported building pack schema")
    payload = (root / "buildings.json").resolve()
    if not payload.is_relative_to(root) or payload.stat().st_size > 10*1024*1024:
        raise ValueError("Building payload must remain inside pack and below 10 MB")
    content = payload.read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest["sha256"]:
        raise ValueError("Building checksum mismatch")
    data = json.loads(content)
    return LocalBuildingState(tuple(LocalBuilding(tuple(tuple(p) for p in b["ring_rad"]),
                              b["height_m"], b["height_source"]) for b in data["buildings"]),
                              data["attribution"])
