# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for map-builder vector tile validation."""

from __future__ import annotations

import unittest

from tools.map_builder.builder.validate import _decode_vector_tile, _validate_geometry


def _varint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def _field(number: int, payload: bytes) -> bytes:
    return _varint((number << 3) | 2) + _varint(len(payload)) + payload


def _zigzag(value: int) -> int:
    return (value << 1) ^ (value >> 31)


class GeometryValidationTest(unittest.TestCase):
    def test_accepts_normal_geometry(self):
        geometry = b"".join(
            _varint(value)
            for value in (
                (1 << 3) | 1,
                _zigzag(100),
                _zigzag(200),
                (2 << 3) | 2,
                _zigzag(10),
                _zigzag(-20),
                _zigzag(30),
                _zigzag(40),
            )
        )
        _validate_geometry(
            geometry,
            layer_name="transportation",
            feature_index=3,
            feature_id=42,
        )

    def test_rejects_maplibre_int16_coordinate_overflow(self):
        geometry = b"".join(
            _varint(value)
            for value in (
                (1 << 3) | 1,
                _zigzag(32768),
                _zigzag(0),
            )
        )
        with self.assertRaisesRegex(
            ValueError,
            r"paths outside valid range of coordinate_type: .*coordinate=\(32768,0\)",
        ):
            _validate_geometry(
                geometry,
                layer_name="water",
                feature_index=7,
                feature_id=None,
            )

    def test_rejects_truncated_coordinate_pair(self):
        geometry = b"".join(
            _varint(value)
            for value in (
                (1 << 3) | 1,
                _zigzag(12),
            )
        )
        with self.assertRaisesRegex(ValueError, "truncated geometry coordinate pair"):
            _validate_geometry(
                geometry,
                layer_name="road",
                feature_index=0,
                feature_id=None,
            )


class VectorTileValidationTest(unittest.TestCase):
    def test_decodes_minimal_vector_tile_without_external_dependencies(self):
        geometry = b"".join(
            _varint(value)
            for value in (
                (1 << 3) | 1,
                _zigzag(12),
                _zigzag(34),
            )
        )
        feature = _field(4, geometry)
        layer = _field(1, b"place") + _field(2, feature)
        tile = _field(3, layer)

        self.assertEqual(
            {"layers": 1, "features": 1},
            _decode_vector_tile(tile),
        )


if __name__ == "__main__":
    unittest.main()
