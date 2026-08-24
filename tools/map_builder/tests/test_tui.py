# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from pathlib import Path
import unittest

from tools.map_builder.builder.geofabrik import load_index, region_map
from tools.map_builder.builder.tui import expanded_ancestors, visible_regions

FIXTURE = Path(__file__).parent / "fixtures/geofabrik-index.json"


class VisibleRegionsTests(unittest.TestCase):
    def setUp(self):
        self.regions = load_index(FIXTURE)

    def test_collapsed_tree_only_shows_roots(self):
        visible = visible_regions(self.regions, set())

        self.assertEqual([item.region.id for item in visible], ["north-america"])
        self.assertTrue(visible[0].has_children)
        self.assertEqual(visible[0].depth, 0)

    def test_expanding_parents_reveals_children(self):
        visible = visible_regions(self.regions, {"north-america", "north-america/us"})

        self.assertEqual(
            [item.region.id for item in visible],
            [
                "north-america",
                "north-america/us",
                "north-america/us/michigan",
                "north-america/us/ohio",
            ],
        )
        self.assertEqual([item.depth for item in visible], [0, 1, 2, 2])

    def test_search_shows_matches_and_their_ancestors(self):
        visible = visible_regions(self.regions, set(), "mich")

        self.assertEqual(
            [item.region.id for item in visible],
            ["north-america", "north-america/us", "north-america/us/michigan"],
        )

    def test_search_is_case_insensitive(self):
        visible = visible_regions(self.regions, set(), "UNITED STATES")

        self.assertEqual(
            [item.region.id for item in visible],
            ["north-america", "north-america/us"],
        )

    def test_selected_region_ancestors_are_expanded(self):
        expanded = expanded_ancestors(
            {"north-america/us/michigan"},
            region_map(self.regions),
        )

        self.assertEqual(expanded, {"north-america", "north-america/us"})


if __name__ == "__main__":
    unittest.main()
