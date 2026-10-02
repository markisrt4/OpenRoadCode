# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import argparse
import unittest

from controllers.poi.poi_models import PoiCategory
from controllers.poi.poi_search_cli import _parse_category


class PoiSearchCliTest(unittest.TestCase):
    def test_parse_direct_categories(self) -> None:
        self.assertIs(_parse_category("food"), PoiCategory.FOOD)
        self.assertIs(_parse_category("fuel"), PoiCategory.FUEL)
        self.assertIs(_parse_category("grocery"), PoiCategory.GROCERY)

    def test_parse_human_aliases(self) -> None:
        self.assertIs(_parse_category("gas"), PoiCategory.FUEL)
        self.assertIs(_parse_category("restaurant"), PoiCategory.FOOD)
        self.assertIs(_parse_category("supermarket"), PoiCategory.GROCERY)

    def test_reject_unknown_category(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            _parse_category("spaceship")


if __name__ == "__main__":
    unittest.main()
