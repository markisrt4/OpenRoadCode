# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validate generated OpenRoadCode map artifacts."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sqlite3
import subprocess
from pathlib import Path


class ValidationError(RuntimeError):
    """Raised when generated navigation data fails validation."""


def _run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True, check=True)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_pbf(path):
    if not path.is_file() or path.stat().st_size == 0:
        raise ValidationError(f"Missing/empty OSM PBF: {path}")
    _run(["osmium", "fileinfo", "-e", str(path)])


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    for _ in range(10):
        if offset >= len(data):
            raise ValueError("truncated protobuf varint")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
    raise ValueError("protobuf varint is too long")


def _iter_protobuf_fields(data: bytes):
    offset = 0
    while offset < len(data):
        key, offset = _read_varint(data, offset)
        field_number = key >> 3
        wire_type = key & 0x07
        if field_number == 0:
            raise ValueError("protobuf field number 0 is invalid")
        if wire_type == 0:
            value, offset = _read_varint(data, offset)
            yield field_number, wire_type, value
        elif wire_type == 1:
            end = offset + 8
            if end > len(data):
                raise ValueError("truncated protobuf fixed64 field")
            yield field_number, wire_type, data[offset:end]
            offset = end
        elif wire_type == 2:
            length, offset = _read_varint(data, offset)
            end = offset + length
            if end > len(data):
                raise ValueError("truncated protobuf length-delimited field")
            yield field_number, wire_type, data[offset:end]
            offset = end
        elif wire_type == 5:
            end = offset + 4
            if end > len(data):
                raise ValueError("truncated protobuf fixed32 field")
            yield field_number, wire_type, data[offset:end]
            offset = end
        else:
            raise ValueError(f"unsupported protobuf wire type {wire_type}")


def _decode_packed_varints(data: bytes) -> list[int]:
    values = []
    offset = 0
    while offset < len(data):
        value, offset = _read_varint(data, offset)
        values.append(value)
    return values


def _decode_zigzag32(value: int) -> int:
    value &= 0xFFFFFFFF
    return (value >> 1) ^ -(value & 1)


def _validate_geometry(
    geometry: bytes,
    *,
    layer_name: str,
    feature_index: int,
    feature_id: int | None,
) -> None:
    """Validate an MVT geometry command stream using MapLibre's int16 range."""
    values = _decode_packed_varints(geometry)
    index = 0
    x = 0
    y = 0
    min_coord = -(1 << 15)
    max_coord = (1 << 15) - 1

    while index < len(values):
        command_header = values[index]
        index += 1
        command = command_header & 0x07
        count = command_header >> 3
        if count == 0:
            raise ValueError("geometry command has zero repeat count")

        if command in (1, 2):  # MoveTo, LineTo
            required = count * 2
            if index + required > len(values):
                raise ValueError("truncated geometry coordinate pair")
            for _ in range(count):
                x += _decode_zigzag32(values[index])
                y += _decode_zigzag32(values[index + 1])
                index += 2
                if not (min_coord <= x <= max_coord and min_coord <= y <= max_coord):
                    identity = (
                        f"layer={layer_name!r} feature_index={feature_index}"
                        + (f" feature_id={feature_id}" if feature_id is not None else "")
                    )
                    raise ValueError(
                        "paths outside valid range of coordinate_type: "
                        f"{identity} coordinate=({x},{y})"
                    )
        elif command == 7:  # ClosePath
            # ClosePath consumes no coordinate parameters. MapLibre also forces
            # the remaining repeat count to zero, so one encoded ClosePath is
            # the meaningful form for vector-tile geometry.
            continue
        else:
            raise ValueError(f"unknown geometry command {command}")


def _parse_feature(feature: bytes) -> tuple[int | None, bytes | None]:
    feature_id = None
    geometry = None
    for field_number, wire_type, value in _iter_protobuf_fields(feature):
        if field_number == 1 and wire_type == 0:
            feature_id = int(value)
        elif field_number == 4 and wire_type == 2:
            geometry = value
    return feature_id, geometry


def _validate_layer(layer: bytes) -> int:
    name = "<unnamed>"
    features = []
    for field_number, wire_type, value in _iter_protobuf_fields(layer):
        if field_number == 1 and wire_type == 2:
            name = value.decode("utf-8", errors="replace")
        elif field_number == 2 and wire_type == 2:
            features.append(value)

    for feature_index, feature in enumerate(features):
        feature_id, geometry = _parse_feature(feature)
        if geometry is None:
            continue
        _validate_geometry(
            geometry,
            layer_name=name,
            feature_index=feature_index,
            feature_id=feature_id,
        )
    return len(features)


def _decode_vector_tile(blob: bytes) -> dict:
    """Decode enough MVT structure to validate every feature geometry."""
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)

    layers = 0
    features = 0
    for field_number, wire_type, value in _iter_protobuf_fields(blob):
        if field_number == 3 and wire_type == 2:
            layers += 1
            features += _validate_layer(value)
    if layers == 0:
        raise ValueError("vector tile contains no layers")
    return {"layers": layers, "features": features}


def _vector_tile_rows(db, tile_count):
    full_scan = os.environ.get("OPENROAD_VECTOR_TILE_FULL_SCAN", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    limit = int(os.environ.get("OPENROAD_VECTOR_TILE_SCAN_LIMIT", "0"))
    if full_scan:
        return db.execute(
            "SELECT zoom_level,tile_column,tile_row,tile_data "
            "FROM tiles ORDER BY zoom_level,tile_column,tile_row"
        )
    if limit <= 0:
        return ()
    zooms = [
        row[0]
        for row in db.execute(
            "SELECT DISTINCT zoom_level FROM tiles ORDER BY zoom_level"
        )
    ]
    per_zoom = max(1, limit // max(1, len(zooms)))
    rows = []
    for zoom in zooms:
        rows.extend(
            db.execute(
                "SELECT zoom_level,tile_column,tile_row,tile_data "
                "FROM tiles WHERE zoom_level=? ORDER BY tile_column,tile_row LIMIT ?",
                (zoom, per_zoom),
            )
        )
    return rows[:limit]


def validate_vector_tiles(db, tile_count):
    rows = _vector_tile_rows(db, tile_count)
    checked = 0
    features = 0
    for zoom, column, row, blob in rows:
        try:
            decoded = _decode_vector_tile(blob)
        except Exception as exc:
            xyz_row = (1 << zoom) - 1 - row
            raise ValidationError(
                f"Invalid vector tile z={zoom} x={column} "
                f"tms_y={row} xyz_y={xyz_row}: {exc}"
            ) from exc
        checked += 1
        features += decoded["features"]
    return {"checked": checked, "features": features, "decoder": "builtin-mvt"}


def validate_mbtiles(path):
    if not path.is_file() or path.stat().st_size == 0:
        raise ValidationError(f"Missing/empty MBTiles: {path}")
    with sqlite3.connect(path) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValidationError(f"MBTiles integrity check failed: {integrity}")
        tile_count = db.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        metadata = dict(db.execute("SELECT name, value FROM metadata"))
        vector_validation = validate_vector_tiles(db, tile_count)
    if tile_count <= 0:
        raise ValidationError("MBTiles contains no tiles")
    layers = {
        item.get("id")
        for item in json.loads(metadata.get("json", "{}")).get("vector_layers", [])
        if isinstance(item, dict)
    }
    missing = {"transportation", "transportation_name"} - layers
    if missing:
        raise ValidationError(
            "MBTiles missing required layer(s): " + ", ".join(sorted(missing))
        )
    return {
        "tiles": tile_count,
        "layers": sorted(item for item in layers if item),
        "vector_tiles": vector_validation,
    }


def validate_style(path, available_layers=None):
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = data.get("sources") or {}
    if data.get("version") != 8:
        raise ValidationError("Style is not MapLibre/Mapbox Style Spec version 8")
    for source in ("openroad", "route", "vehicle"):
        if source not in sources:
            raise ValidationError(f"Style missing source: {source}")
    for source in ("vehicle", "route"):
        if (sources[source].get("data") or {}).get("type") != "FeatureCollection":
            raise ValidationError(f"{source.title()} GeoJSON source is malformed")
    if available_layers is not None:
        referenced = {
            layer.get("source-layer")
            for layer in data.get("layers", [])
            if layer.get("source") == "openroad" and layer.get("source-layer")
        }
        missing = referenced - set(available_layers)
        if missing:
            raise ValidationError(
                "Style references unavailable MBTiles layer(s): "
                + ", ".join(sorted(missing))
            )


def validate_glyphs(path):
    files = list(path.rglob("*.pbf")) if path.exists() else []
    if len(files) < 10 or not any(item.name == "0-255.pbf" for item in files):
        raise ValidationError(f"Invalid glyph set under {path}")
    return len(files)


def validate_valhalla(root, *, service_smoke=False):
    config = root / "valhalla.json"
    tiles = root / "tiles"
    extract = root / "tiles.tar"
    admins = root / "admins.sqlite"
    timezones = root / "timezones.sqlite"
    json.loads(config.read_text(encoding="utf-8"))
    tile_files = [item for item in tiles.rglob("*") if item.is_file()]
    if not tile_files:
        raise ValidationError("Valhalla tile directory is empty")
    for db_path in (admins, timezones):
        if not db_path.is_file() or db_path.stat().st_size == 0:
            raise ValidationError(f"Missing/empty Valhalla database: {db_path}")
        with sqlite3.connect(db_path) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValidationError(f"SQLite integrity failed: {db_path}")
    if not extract.is_file() or extract.stat().st_size == 0:
        raise ValidationError("Valhalla tile extract is missing or empty")
    result = {"tile_files": len(tile_files), "extract_bytes": extract.stat().st_size}
    if service_smoke:
        import time
        import urllib.request

        proc = subprocess.Popen(
            ["valhalla_service", str(config), "1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(30):
                try:
                    with urllib.request.urlopen(
                        "http://127.0.0.1:8002/status", timeout=1
                    ) as response:
                        if response.status == 200:
                            result["service_status"] = "ok"
                            break
                except Exception:
                    time.sleep(0.5)
            else:
                raise ValidationError("Valhalla service smoke test failed")
        finally:
            proc.terminate()
    return result


def validate_output(root, *, service_smoke=False):
    pbfs = sorted((root / "maps/source").glob("*.osm.pbf"))
    if not pbfs:
        raise ValidationError("No source PBFs found")
    for pbf in pbfs:
        validate_pbf(pbf)
    mbtiles = root / "maps/vector/openroadcode.mbtiles"
    style = root / "maps/styles/openroadcode.json"
    valhalla = root / "valhalla"
    result = {
        "source_pbfs": len(pbfs),
        "mbtiles": validate_mbtiles(mbtiles),
        "glyph_files": validate_glyphs(root / "maps/glyphs"),
        "valhalla": validate_valhalla(valhalla, service_smoke=service_smoke),
    }
    validate_style(style, result["mbtiles"]["layers"])
    result["checksums"] = {
        "mbtiles": sha256(mbtiles),
        "style": sha256(style),
        "valhalla_extract": sha256(valhalla / "tiles.tar"),
    }
    return result
