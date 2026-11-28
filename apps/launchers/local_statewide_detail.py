"""Verified statewide detail index with bounded on-demand imagery/terrain reads."""

import hashlib
import json
import math
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from apps.launchers.local_imagery_pyramid import LocalImageryPyramidPack
from apps.launchers.local_terrain_pack import LocalTerrainCatalog, _load_single_terrain
from common.xdg_paths import openroadcode_data_dir
from development.maps.statewide_detail_plan import (
    IMAGE_ZOOM,
    PROFILE,
    ROOT_ZOOM,
    bounds,
    cell_id,
    parse_cell,
    xy,
)
from ui.navigation.local_imagery_state import LocalImageryPyramidState, LocalImageryState
from ui.navigation.local_terrain_state import LocalPagedTerrainState, LocalTerrainTileIndexState


class StatewideDetailIndex:
    def __init__(self, root, document):
        self.root = Path(root).resolve()
        rows = document.get("cells", [])
        if document.get("profile") != PROFILE or not 1 <= len(rows) <= 768:
            raise ValueError("Invalid statewide detail catalog")
        self.cells = {}
        self._images = OrderedDict()
        self._terrain = OrderedDict()
        self._mosaics = OrderedDict()
        self._lock = threading.RLock()
        for row in rows:
            key = row.get("id", "")
            digest = row.get("sha256", "")
            if (
                not re.fullmatch(r"mi-z10-[0-9]{1,4}-[0-9]{1,4}", key)
                or not re.fullmatch("[a-f0-9]{64}", digest)
                or key in self.cells
            ):
                raise ValueError("Invalid detail cell identifier/checksum")
            x, y = parse_cell(key)
            directory = (self.root / "cells" / (key + "-" + digest)).resolve()
            if not directory.is_relative_to(self.root / "cells"):
                raise ValueError("Detail cell escapes managed storage")
            manifest = json.loads((directory / "manifest.json").read_text())
            if manifest.get("id") != key or manifest.get("profile") != PROFILE:
                raise ValueError("Detail cell identity mismatch")
            if len(manifest["bounds_deg"]) != 4 or any(
                abs(a - b) > 1e-9 for a, b in zip(manifest["bounds_deg"], bounds(x, y), strict=True)
            ):
                raise ValueError("Detail cell bounds mismatch")
            self.cells[key] = (directory, manifest)

    @property
    def coverage(self):
        bounds = [m["bounds_deg"] for _, m in self.cells.values()]
        return LocalImageryState(
            "Michigan offline detail",
            "USDA NAIP / USGS · The National Map",
            *(
                math.radians(v)
                for v in (
                    min(b[0] for b in bounds),
                    min(b[1] for b in bounds),
                    max(b[2] for b in bounds),
                    max(b[3] for b in bounds),
                )
            ),
        )

    def image(self, zoom, x, y):
        if (
            any(type(v) is not int for v in (zoom, x, y))
            or not 0 <= zoom <= IMAGE_ZOOM
            or not 0 <= x < 2**zoom
            or not 0 <= y < 2**zoom
        ):
            raise ValueError("Invalid statewide imagery address")
        if zoom < ROOT_ZOOM:
            return None
        key = cell_id(x >> (zoom - ROOT_ZOOM), y >> (zoom - ROOT_ZOOM))
        if key not in self.cells:
            return None
        directory, manifest = self.cells[key]
        if not manifest.get("imagery_available"):
            return None
        with self._lock:
            database = directory / "imagery/imagery.mbtiles"
            stat = database.stat()
            stamp = (stat.st_size, stat.st_mtime_ns)
            cached = self._images.get(key)
            if cached is None or cached[0] != stamp:
                cached = (stamp, LocalImageryPyramidPack.load(directory / "imagery"))
                self._images[key] = cached
            self._images.move_to_end(key)
            while len(self._images) > 4:
                self._images.popitem(last=False)
            return cached[1].tile(zoom, x, y)

    def _chunk(self, key):
        match = re.fullmatch(r"(mi-z10-[0-9]{1,4}-[0-9]{1,4})--([0-9]{1,2})", key)
        if not match or match[1] not in self.cells:
            raise ValueError("Unknown terrain detail chunk")
        directory, manifest = self.cells[match[1]]
        if not manifest.get("terrain_available"):
            raise ValueError("No terrain for detail cell")
        terrain_root = directory / "terrain"
        mosaic = json.loads((terrain_root / "manifest.json").read_text())
        index = int(match[2])
        if index >= len(mosaic["tiles"]):
            raise ValueError("Unknown terrain detail chunk")
        record = mosaic["tiles"][index]
        path = (terrain_root / record["path"]).resolve()
        if not path.is_relative_to(terrain_root.resolve()):
            raise ValueError("Terrain detail escapes pack")
        payload = path / "terrain.json"
        stat = payload.stat()
        stamp = (stat.st_size, stat.st_mtime_ns)
        with self._lock:
            cached = self._terrain.get(key)
            if cached is None or cached[0] != stamp:
                if stat.st_size > 2 * 1024 * 1024:
                    raise ValueError("Oversized terrain detail chunk")
                content = payload.read_bytes()
                if hashlib.sha256(content).hexdigest() != record["sha256"]:
                    raise ValueError("Terrain detail checksum mismatch")
                state = _load_single_terrain(path, detail_level=7, minimum_zoom=12)
                cached = (stamp, state, content)
                self._terrain[key] = cached
            self._terrain.move_to_end(key)
            while len(self._terrain) > 32:
                self._terrain.popitem(last=False)
            return cached

    def chunk(self, key):
        return self._chunk(key)[2]

    def point_sources(self, longitude, latitude):
        from apps.launchers.terrain_mesh_sampler import TerrainSource

        lon, lat = math.degrees(longitude), math.degrees(latitude)
        column, row = xy(lon, lat)
        w, s, e, n = bounds(column, row)
        # A root can have 1–8 subdivisions. Two samples of the widest child
        # cover every possible blending halo, including an adjoining root.
        dx, dy = 2 * (e - w) / 128, 2 * (n - s) / 128
        left, top = xy(lon - dx, lat + dy)
        right, bottom = xy(lon + dx, lat - dy)
        rows = []
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                key = cell_id(x, y)
                if key not in self.cells:
                    continue
                directory, manifest = self.cells[key]
                if not manifest.get("terrain_available"):
                    continue
                with self._lock:
                    if key not in self._mosaics:
                        mosaic = json.loads((directory / "terrain/manifest.json").read_text())
                        sources = []
                        for index, record in enumerate(mosaic["tiles"]):
                            identity = key + "--" + str(index)
                            sources.append(
                                TerrainSource(
                                    "mi-point-" + identity,
                                    tuple(math.radians(value) for value in record["bounds_deg"]),
                                    129,
                                    129,
                                    7,
                                    lambda identity=identity: self._chunk(identity)[1],
                                )
                            )
                        self._mosaics[key] = tuple(sources)
                    self._mosaics.move_to_end(key)
                    sources = self._mosaics[key]
                    while len(self._mosaics) > 8:
                        self._mosaics.popitem(last=False)
                rows.extend(source for source in sources if source.supports(longitude, latitude))
        return rows

    def page(self, zoom, x, y, reference):
        if (
            any(type(v) is not int for v in (zoom, x, y))
            or not 0 <= zoom <= 16
            or not 0 <= x < 2 ** (zoom + 1)
            or not 0 <= y < 2**zoom
        ):
            raise ValueError("Invalid terrain detail page address")
        if zoom < 12:
            return {"tiles": []}
        w = x / 2 ** (zoom + 1) * 360 - 180
        e = (x + 1) / 2 ** (zoom + 1) * 360 - 180
        n = 90 - y / 2**zoom * 180
        s = 90 - (y + 1) / 2**zoom * 180
        px = (e - w) / 32
        py = (n - s) / 32
        w = max(-180, w - px)
        e = min(180, e + px)
        s = max(-90, s - py)
        n = min(90, n + py)
        left, top = xy(w, n)
        right, bottom = xy(e, s)
        selected = []
        for row in range(top, bottom + 1):
            for column in range(left, right + 1):
                key = cell_id(column, row)
                if key not in self.cells:
                    continue
                directory, manifest = self.cells[key]
                if not manifest.get("terrain_available"):
                    continue
                mosaic = json.loads((directory / "terrain/manifest.json").read_text())
                for index, record in enumerate(mosaic["tiles"]):
                    a, b, c, d = record["bounds_deg"]
                    if a > e or c < w or b > n or d < s:
                        continue
                    identity = key + "--" + str(index)
                    state = self._chunk(identity)[1]
                    metadata = LocalTerrainTileIndexState(
                        identity,
                        state.coverage,
                        state.width,
                        state.height,
                        reference,
                        state.vertical_datum,
                        7,
                        12,
                    ).document()
                    metadata["url"] = "/data/terrain-chunk/" + identity
                    selected.append(metadata)
        if len(selected) > 64:
            raise ValueError("Terrain detail page exceeds 64 grids")
        return {"tiles": selected}


@dataclass(frozen=True)
class StatewideImagery:
    index: StatewideDetailIndex

    @property
    def state(self):
        return LocalImageryPyramidState(self.index.coverage, ROOT_ZOOM, IMAGE_ZOOM, "webp")

    def tile(self, zoom, x, y):
        return self.index.image(zoom, x, y)


@dataclass(frozen=True)
class PagedTerrainCatalog(LocalTerrainCatalog):
    index: StatewideDetailIndex

    def page(self, zoom, x, y):
        reference = self.state.tiles[0].reference_height_m if self.state.tiles else 0
        return self.index.page(zoom, x, y, reference)

    def chunk(self, key):
        return self.index.chunk(key)


def installed_index():
    root = openroadcode_data_dir("map-packs", "michigan-detail")
    path = root / "active/catalog.json"
    if not path.is_file():
        return None
    return StatewideDetailIndex(root, json.loads(path.read_text()))


def paged_terrain(baseline):
    index = installed_index()
    from apps.launchers.local_us_terrain import CombinedTerrainIndex, installed_national_index

    national = installed_national_index()
    if index is None and national is None:
        return baseline
    maximum_zoom = 16 if index is not None else baseline.state.maximum_zoom if baseline else 10
    if national is not None:
        index = CombinedTerrainIndex(index, national)
    state = LocalPagedTerrainState(
        baseline.state.tiles if baseline else (),
        maximum_zoom=maximum_zoom,
        page_minimum_zoom=8 if national else 12,
    )
    return PagedTerrainCatalog(state, baseline.payloads if baseline else (), index)
