# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import unittest

from tools.map_builder.builder.build import BuildError, _parse_bbox


class BoundingBoxTests(unittest.TestCase):
    def test_parse_plain_bbox(self):
        self.assertEqual(
            _parse_bbox("-90.5,41.2,-80.1,48.3"),
            "-90.5,41.2,-80.1,48.3",
        )

    def test_parse_osmium_box_format(self):
        self.assertEqual(
            _parse_bbox("BOX(-90.5 41.2,-80.1 48.3)"),
            "-90.5,41.2,-80.1,48.3",
        )

    def test_reject_invalid_bbox(self):
        with self.assertRaises(BuildError):
            _parse_bbox("not a bounding box")

        with self.assertRaises(BuildError):
            _parse_bbox("10,20,-10,30")


if __name__ == "__main__":
    unittest.main()
