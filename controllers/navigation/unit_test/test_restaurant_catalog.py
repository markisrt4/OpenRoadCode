"""Tests for resolving map restaurant POIs to ordering destinations."""
from __future__ import annotations

import unittest

from controllers.navigation.restaurant_catalog import resolve_restaurant_poi


class RestaurantCatalogTest(unittest.TestCase):
    def test_resolves_panera_from_brand(self) -> None:
        destination = resolve_restaurant_poi(brand="Panera Bread")
        self.assertIsNotNone(destination)
        assert destination is not None
        self.assertEqual(destination.android_package, "com.panera.bread")
        self.assertIn("panerabread.com", destination.order_url)

    def test_resolves_mcdonalds_despite_punctuation(self) -> None:
        destination = resolve_restaurant_poi(name="McDonalds")
        self.assertIsNotNone(destination)
        assert destination is not None
        self.assertEqual(destination.brand, "McDonald's")

    def test_prefers_brand_over_location_name(self) -> None:
        destination = resolve_restaurant_poi(brand="Panera", name="Hall Road Cafe")
        self.assertIsNotNone(destination)
        assert destination is not None
        self.assertEqual(destination.brand, "Panera Bread")

    def test_unknown_restaurant_has_no_order_mapping(self) -> None:
        self.assertIsNone(resolve_restaurant_poi(name="Bob's Mysterious Sandwich Shed"))


if __name__ == "__main__":
    unittest.main()
