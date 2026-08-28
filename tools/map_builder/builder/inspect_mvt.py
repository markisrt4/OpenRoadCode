# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Inspect features and MapLibre coordinate overflows in MBTiles vector tiles."""
from __future__ import annotations

import argparse
import gzip
import math
import sqlite3
import struct
from collections import Counter
from pathlib import Path

from .validate import (
    _decode_packed_varints,
    _decode_zigzag32,
    _iter_protobuf_fields,
)


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


def _geometry_overflows(geometry: bytes) -> list[tuple[int, int]]:
    """Return coordinates outside MapLibre Native's signed int16 range."""
    values = _decode_packed_varints(geometry)
    index = 0
    x = 0
    y = 0
    overflows = []
    min_coord = -(1 << 15)
    max_coord = (1 << 15) - 1

    while index < len(values):
        command_header = values[index]
        index += 1
        command = command_header & 0x07
        count = command_header >> 3
        if count == 0:
            raise ValueError("geometry command has zero repeat count")
        if command in (1, 2):
            required = count * 2
            if index + required > len(values):
                raise ValueError("truncated geometry coordinate pair")
            for _ in range(count):
                x += _decode_zigzag32(values[index])
                y += _decode_zigzag32(values[index + 1])
                index += 2
                if not (min_coord <= x <= max_coord and min_coord <= y <= max_coord):
                    overflows.append((x, y))
        elif command == 7:
            continue
        else:
            raise ValueError(f"unknown geometry command {command}")
    return overflows


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


def _feature_name(attributes: dict) -> str:
    for key in ("name", "name:latin", "name:en"):
        value = attributes.get(key)
        if value:
            return str(value)
    return "<unnamed>"


def survey_invalid_tiles(
    mbtiles: Path,
    *,
    zoom: int | None = None,
    max_samples: int = 25,
) -> int:
    """Scan vector features and summarize MapLibre coordinate overflows."""
    layer_counts: Counter[str] = Counter()
    class_counts: Counter[tuple[str, str]] = Counter()
    overflow_features = 0
    overflow_coordinates = 0
    checked_tiles = 0
    checked_features = 0
    samples = []

    query = (
        "SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles "
        + ("WHERE zoom_level=? " if zoom is not None else "")
        + "ORDER BY zoom_level,tile_column,tile_row"
    )
    params = (zoom,) if zoom is not None else ()

    with sqlite3.connect(mbtiles) as db:
        for z, x, tms_y, blob in db.execute(query, params):
            checked_tiles += 1
            xyz_y = (1 << z) - 1 - tms_y
            for feature in inspect_tile(blob):
                checked_features += 1
                overflows = _geometry_overflows(feature["geometry"])
                if not overflows:
                    continue

                overflow_features += 1
                overflow_coordinates += len(overflows)
                layer = feature["layer"]
                feature_class = str(feature["attributes"].get("class", "<none>"))
                layer_counts[layer] += 1
                class_counts[(layer, feature_class)] += 1
                if len(samples) < max_samples:
                    samples.append(
                        {
                            "z": z,
                            "x": x,
                            "xyz_y": xyz_y,
                            "layer": layer,
                            "feature_index": feature["feature_index"],
                            "feature_id": feature["feature_id"],
                            "class": feature_class,
                            "name": _feature_name(feature["attributes"]),
                            "coordinate": overflows[0],
                        }
                    )

    print(
        f"checked_tiles={checked_tiles} checked_features={checked_features} "
        f"overflow_features={overflow_features} "
        f"overflow_coordinates={overflow_coordinates}"
    )
    if not overflow_features:
        print("No MapLibre int16 coordinate overflows found.")
        return 0

    print("\nOverflow features by layer:")
    for layer, count in layer_counts.most_common():
        print(f"  {layer}: {count}")

    print("\nOverflow features by layer/class:")
    for (layer, feature_class), count in class_counts.most_common():
        print(f"  {layer}/{feature_class}: {count}")

    print(f"\nFirst {len(samples)} overflow feature(s):")
    for sample in samples:
        print(
            "  "
            f"z={sample['z']} x={sample['x']} xyz_y={sample['xyz_y']} "
            f"layer={sample['layer']!r} index={sample['feature_index']} "
            f"id={sample['feature_id']} class={sample['class']!r} "
            f"name={sample['name']!r} coordinate={sample['coordinate']}"
        )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mbtiles", type=Path)
    parser.add_argument("--scan-invalid", action="store_true")
    parser.add_argument("--scan-zoom", type=int)
    parser.add_argument("--max-samples", type=int, default=25)
    parser.add_argument("--z", type=int)
    parser.add_argument("--x", type=int)
    parser.add_argument("--xyz-y", type=int)
    parser.add_argument("--layer")
    parser.add_argument("--feature-index", type=int)
    args = parser.parse_args()

    if args.scan_invalid:
        return survey_invalid_tiles(
            args.mbtiles,
            zoom=args.scan_zoom,
            max_samples=max(0, args.max_samples),
        )

    if args.z is None or args.x is None or args.xyz_y is None:
        parser.error("--z, --x, and --xyz-y are required unless --scan-invalid is used")

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
        overflows = _geometry_overflows(feature["geometry"])
        if overflows:
            print(f"maplibre_int16_overflows={overflows}")

    if found == 0:
        raise SystemExit("no matching feature found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
