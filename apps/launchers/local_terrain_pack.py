"""Read a bounded local terrain pack without introducing renderer dependencies."""

import hashlib
import json
import math
from pathlib import Path

from common.xdg_paths import openroadcode_data_dir
from common.navigation_data import navigation_data_root
from ui.navigation.local_imagery_state import LocalImageryState
from ui.navigation.local_terrain_state import LocalTerrainState


def detroit_terrain_directory():
    return openroadcode_data_dir("map-packs", "detroit-terrain-v1")


def preferred_terrain_directory():
    packs = navigation_data_root()/'maps/3d/packs'
    for key in ('detroit-midtown-terrain', 'detroit-downtown-terrain'):
        if (packs/key/'manifest.json').is_file():
            return packs/key
    return detroit_terrain_directory()


def load_terrain(directory):
    root = Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported terrain schema")
    payload = (root / "terrain.json").resolve()
    if not payload.is_relative_to(root):
        raise ValueError("Terrain data must remain inside the pack")
    if payload.stat().st_size > 2*1024*1024:
        raise ValueError("Prototype terrain exceeds 2 MB")
    content = payload.read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest["sha256"]:
        raise ValueError("Terrain checksum does not match manifest")
    data = json.loads(content)
    coverage = LocalImageryState(manifest["title"], manifest["attribution"],
                                 *(math.radians(v) for v in manifest["bounds_deg"]))
    return LocalTerrainState(coverage, data["width"], data["height"], tuple(data["heights_m"]),
                              data["reference_height_m"], data["vertical_datum"])
