# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify the installer separates development tools from runtime packages."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


FEATURES = Path(__file__).resolve().parents[1] / "installer_features.sh"


class DevelopmentToolsTests(unittest.TestCase):
    def feature_output(self, function: str, argument: str) -> list[str]:
        result = subprocess.run(
            ["bash", "-c", 'source "$1"; "$2" "$3"',
             "feature-test", str(FEATURES), function, argument],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout.split()

    def test_development_tools_are_known(self) -> None:
        self.assertIn("dev-tools", self.feature_output("get_known_features", ""))

    def test_linux_all_features_include_development_tools(self) -> None:
        self.assertIn("dev-tools", self.feature_output("get_all_features_for_target", "linux-dev"))

    def test_development_tools_install_pytest_and_ruff(self) -> None:
        self.assertEqual(["pytest", "ruff"], self.feature_output("get_feature_python_packages", "dev-tools"))
        self.assertNotIn("ruff", self.feature_output("get_feature_packages", "base"))

    def test_runtime_dependencies_remain_in_their_features(self) -> None:
        for feature, expected in (
            ("base", {"requests", "tomli", "pyzmq"}),
            ("desktop-ui", {"Pillow", "tinycss2"}),
            ("web-ui", {"Flask"}),
        ):
            with self.subTest(feature=feature):
                self.assertTrue(expected.issubset(set(self.feature_output("get_feature_python_packages", feature))))


if __name__ == "__main__":
    unittest.main()
