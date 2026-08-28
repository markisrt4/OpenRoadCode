# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Inspect features and tags in one MBTiles vector tile."""
from __future__ import annotations

import argparse
import gzip
import math
import sqlite3
import struct
from pathlib import Path

from .validate import _decode_packed_varints, _iter_protobuf_fields


def _decode_zigzag64(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def _decode_value(data: bytes):
    for field_number, wire_type, value in _iter_protobuf_fields(data):
        if field_number == 1 and wire_type == 2:
            return value.decode("utf-8", errors="replace")
        if field_number == 2 and wire_type == 5:
            return struct.unpack("<f", value)[0]
        if field_number == 3 and wire_type == 1:
            return struct.unpack("<d", value)[0]
        if field_number == 4 and wire_type == 0:
            return int(value)
        if field_number == 5 and wire_type == 0:
            return int(value)
        if field_number == 6 and wire_type == 0:
            return _decode_zigzag64(value)
        if field_number == 7 and wire_type == 0:
            return bool(value)
    return None


def _parse_feature(data: bytes):
    feature_id = None
    tags = []
    geom_type = None
    geometry = b""
    for field_number, wire_type, value in _iter_protobuf_fields(data):
        if field_number == 1 and wire_type == 0:
            feature_id = int(value)
        elif field_number == 2 and wire_type == 2:
            tags.extend(_decode_packed_varints(value))
        elif field_number == 3 and wire_type == 0:
            geom_type = int(value)
        elif field_number == 4 and wire_type == 2:
            geometry = value
    return feature_id, tags, geom_type, geometry


def inspect_tile(blob: bytes) -> list[dict]:
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)

    result = []
    for field_number, wire_type, layer in _iter_protobuf_fields(blob):
        if field_number != 3 or wire_type != 2:
            continue

        layer_name = "<unnamed>"
        keys = []
        values = []
        features = []
        for layer_field, layer_wire, layer_value in _iter_protobuf_fields(layer):
            if layer_field == 1 and layer_wire == 2:
                layer_name = layer_value.decode("utf-8", errors="replace")
            elif layer_field == 2 and layer_wire == 2:
                features.append(layer_value)
            elif layer_field == 3 and layer_wire == 2:
                keys.append(layer_value.decode("utf-8", errors="replace"))
            elif layer_field == 4 and layer_wire == 2:
                values.append(_decode_value(layer_value))

        for index, feature in enumerate(features):
            feature_id, tag_indexes, geom_type, geometry = _parse_feature(feature)
            attrs = {}
            for offset in range(0, len(tag_indexes) - 1, 2):
                key_index = tag_indexes[offset]
                value_index = tag_indexes[offset + 1]
                if key_index < len(keys) and value_index < len(values):
                    attrs[keys[key_index]] = values[value_index]
            result.append(
                {
                    "layer": layer_name,
                    "feature_index": index,
                    "feature_id": feature_id,
                    "geometry_type": geom_type,
                    "geometry": geometry,
                    "attributes": attrs,
                }
            )
    return result


def tile_bounds(z: int, x: int, xyz_y: int) -> tuple[float, float, float, float]:
    n = 1 << z
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0

    def latitude(y: int) -> float:
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))

    north = latitude(xyz_y)
    south = latitude(xyz_y + 1)
    return west, south, east, north


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mbtiles", type=Path)
    parser.add_argument("--z", type=int, required=True)
    parser.add_argument("--x", type=int, required=True)
    parser.add_argument("--xyz-y", type=int, required=True)
    parser.add_argument("--layer")
    parser.add_argument("--feature-index", type=int)
    args = parser.parse_args()

    tms_y = (1 << args.z) - 1 - args.xyz_y
    with sqlite3.connect(args.mbtiles) as db:
        row = db.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (args.z, args.x, tms_y),
        ).fetchone()
    if row is None:
        raise SystemExit("tile not found")

    west, south, east, north = tile_bounds(args.z, args.x, args.xyz_y)
    print(
        f"tile z={args.z} x={args.x} xyz_y={args.xyz_y} tms_y={tms_y} "
        f"bounds=({west:.6f},{south:.6f})..({east:.6f},{north:.6f})"
    )

    found = 0
    for feature in inspect_tile(row[0]):
        if args.layer is not None and feature["layer"] != args.layer:
            continue
        if (
            args.feature_index is not None
            and feature["feature_index"] != args.feature_index
        ):
            continue
        found += 1
        print(
            f"layer={feature['layer']!r} feature_index={feature['feature_index']} "
            f"feature_id={feature['feature_id']} geometry_type={feature['geometry_type']}"
        )
        print(f"attributes={feature['attributes']}")
        print(f"geometry_bytes={feature['geometry'].hex()}")

    if found == 0:
        raise SystemExit("no matching feature found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
