# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Geofabrik region-index handling."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

INDEX_URL = "https://download.geofabrik.de/index-v1-nogeom.json"


@dataclass(frozen=True, slots=True)
class Region:
    id: str
    name: str
    parent: str | None
    pbf_url: str
    iso1: tuple[str, ...] = ()
    iso2: tuple[str, ...] = ()

    @property
    def safe_id(self) -> str:
        return self.id.replace("/", "__")


def _feature_to_region(feature: dict) -> Region | None:
    props = feature.get("properties") or {}
    urls = props.get("urls") or {}
    pbf = urls.get("pbf")
    region_id = props.get("id")
    name = props.get("name")
    if not (isinstance(region_id, str) and isinstance(name, str) and isinstance(pbf, str)):
        return None
    return Region(
        id=region_id,
        name=name,
        parent=props.get("parent") if isinstance(props.get("parent"), str) else None,
        pbf_url=pbf,
        iso1=tuple(props.get("iso3166-1:alpha2") or ()),
        iso2=tuple(props.get("iso3166-2") or ()),
    )


def parse_index(payload: dict) -> list[Region]:
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("Geofabrik index is missing features")
    regions = [r for f in features if isinstance(f, dict) and (r := _feature_to_region(f))]
    regions.sort(key=lambda r: (r.id.count("/"), r.id))
    return regions


def load_index(path: Path) -> list[Region]:
    return parse_index(json.loads(path.read_text(encoding="utf-8")))


def fetch_index(path: Path, *, refresh: bool = False) -> list[Region]:
    if path.exists() and not refresh:
        return load_index(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    request = Request(INDEX_URL, headers={"User-Agent": "OpenRoadCode-map-builder/1.0"})
    with urlopen(request, timeout=60) as response:
        data = response.read()
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)
    return load_index(path)


def region_map(regions: Iterable[Region]) -> dict[str, Region]:
    return {region.id: region for region in regions}


def resolve_region_ids(regions: Iterable[Region], ids: Iterable[str]) -> list[Region]:
    mapping = region_map(regions)
    result: list[Region] = []
    missing: list[str] = []
    for region_id in ids:
        if region_id in mapping:
            result.append(mapping[region_id])
        else:
            missing.append(region_id)
    if missing:
        raise ValueError("Unknown Geofabrik region(s): " + ", ".join(missing))
    validate_selection(result, mapping)
    return result


def _ancestors(region: Region, mapping: dict[str, Region]) -> set[str]:
    result: set[str] = set()
    parent = region.parent
    while parent:
        result.add(parent)
        parent_region = mapping.get(parent)
        parent = parent_region.parent if parent_region else None
    return result


def validate_selection(selected: Iterable[Region], mapping: dict[str, Region]) -> None:
    selected_list = list(selected)
    selected_ids = {r.id for r in selected_list}
    if len(selected_ids) != len(selected_list):
        raise ValueError("Duplicate region selection")
    conflicts: list[tuple[str, str]] = []
    for region in selected_list:
        for ancestor in _ancestors(region, mapping):
            if ancestor in selected_ids:
                conflicts.append((ancestor, region.id))
    if conflicts:
        text = ", ".join(f"{a} + {b}" for a, b in conflicts)
        raise ValueError("Do not select a region together with one of its descendants; that duplicates map data: " + text)
