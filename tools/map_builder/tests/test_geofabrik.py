from pathlib import Path
import unittest

from builder.geofabrik import load_index, region_map, resolve_region_ids, validate_selection

FIXTURE = Path(__file__).parent / "fixtures/geofabrik-index.json"

class GeofabrikTests(unittest.TestCase):
    def setUp(self):
        self.regions = load_index(FIXTURE)
        self.mapping = region_map(self.regions)
    def test_parse_and_resolve_siblings(self):
        selected = resolve_region_ids(self.regions, ["north-america/us/michigan", "north-america/us/ohio"])
        self.assertEqual([x.name for x in selected], ["Michigan", "Ohio"])
    def test_reject_parent_and_child(self):
        with self.assertRaises(ValueError):
            validate_selection([self.mapping["north-america/us"], self.mapping["north-america/us/michigan"]], self.mapping)
    def test_safe_id(self):
        self.assertEqual(self.mapping["north-america/us/michigan"].safe_id, "north-america__us__michigan")

if __name__ == "__main__": unittest.main()
