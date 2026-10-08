"""Tests for the shared documentation inventory."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "docs_inventory.py"
spec = importlib.util.spec_from_file_location("docs_inventory", MODULE_PATH)
assert spec is not None and spec.loader is not None
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class DocsInventoryTests(unittest.TestCase):
    def test_discovery_and_generated_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("README.md", "docs/README.md", "docs/guide.md", "controllers/radio/README.md", "apps/orcUi/ARCHITECTURE.md", "build/README.md"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# " + path.stem + "\n", encoding="utf-8")
            records = inventory.discover(root)
            paths = {record["path"] for record in records}
            self.assertEqual(paths, {"README.md", "docs/README.md", "docs/guide.md", "controllers/radio/README.md", "apps/orcUi/ARCHITECTURE.md"})
            catalog = inventory.render_catalog(records)
            self.assertIn("../controllers/radio/README.md", catalog)
            self.assertIn("../apps/orcUi/ARCHITECTURE.md", catalog)
            self.assertNotIn("build/README.md", catalog)
            self.assertNotIn("](README.md)", catalog)
            original = "Before\n\n" + inventory.BEGIN + "\nold\n" + inventory.END + "\n\nAfter\n"
            updated = inventory.update_index(original, catalog)
            self.assertTrue(updated.startswith("Before\n"))
            self.assertTrue(updated.endswith("After\n"))
            self.assertEqual(inventory.update_index(updated, catalog), updated)
            self.assertEqual(updated.count(inventory.BEGIN), 1)
            self.assertEqual(updated.count(inventory.END), 1)

    def test_missing_or_reversed_markers_fail(self) -> None:
        with self.assertRaises(ValueError):
            inventory.update_index("No markers", "catalog")
        with self.assertRaises(ValueError):
            inventory.update_index(inventory.END + inventory.BEGIN, "catalog")

    def test_new_readme_is_discovered_without_registration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "controllers/new_component/README.md"
            path.parent.mkdir(parents=True)
            path.write_text("# New Component\n", encoding="utf-8")
            records = inventory.discover(root)
            self.assertEqual(records[0]["title"], "New Component")
            self.assertIn("../controllers/new_component/README.md", inventory.render_catalog(records))


if __name__ == "__main__":
    unittest.main()
