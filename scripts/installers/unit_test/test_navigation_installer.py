# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract tests for navigation installer orchestration."""

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
NAV_INSTALLER = (
    PROJECT_ROOT / "scripts" / "installers" / "install_navigation_stack.sh"
)
HOST_INSTALLER = PROJECT_ROOT / "scripts" / "installers" / "host_setup.sh"
SYSTEM_PACKAGES = (
    PROJECT_ROOT / "scripts" / "installers" / "install_system_packages.sh"
)
TERMUX_NAV_BUILDER = (
    PROJECT_ROOT / "development" / "termux" / "build_navigation_stack.sh"
)


class NavigationInstallerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.navigation = NAV_INSTALLER.read_text(encoding="utf-8")
        cls.host_setup = HOST_INSTALLER.read_text(encoding="utf-8")
        cls.system_packages = SYSTEM_PACKAGES.read_text(encoding="utf-8")
        cls.termux_navigation = TERMUX_NAV_BUILDER.read_text(encoding="utf-8")

    def test_host_setup_invokes_navigation_without_recursive_host_setup(self) -> None:
        self.assertIn(
            'bash "$SCRIPT_DIR/install_navigation_stack.sh" \\',
            self.host_setup,
        )
        self.assertIn("--skip-host-packages", self.host_setup)

    def test_navigation_has_independent_component_state_files(self) -> None:
        self.assertIn("maplibre-renderer.sha256", self.navigation)
        self.assertIn("valhalla.sha256", self.navigation)

    def test_navigation_cache_requires_installed_binaries(self) -> None:
        self.assertIn(
            '[[ -x "$INSTALL_ROOT/bin/openroadcode-map-renderer" ]]',
            self.navigation,
        )
        self.assertIn(
            '[[ -x "$INSTALL_ROOT/valhalla/bin/valhalla_service" ]]',
            self.navigation,
        )

    def test_navigation_supports_force_rebuild_overrides(self) -> None:
        self.assertIn("FORCE_NAVIGATION_REBUILD", self.navigation)
        self.assertIn("FORCE_MAPLIBRE_REBUILD", self.navigation)
        self.assertIn("FORCE_VALHALLA_REBUILD", self.navigation)

    def test_docker_is_started_only_for_required_builds(self) -> None:
        self.assertIn(
            "(! SKIP_MAPLIBRE && MAPLIBRE_BUILD_REQUIRED)",
            self.navigation,
        )
        self.assertIn(
            "(! SKIP_VALHALLA && VALHALLA_BUILD_REQUIRED)",
            self.navigation,
        )
        self.assertIn("ensure_container_engine", self.navigation)

    def test_docker_state_is_restored_on_exit(self) -> None:
        self.assertIn("trap restore_container_engine_state EXIT", self.navigation)
        self.assertIn("CONTAINER_ENGINE_STARTED_BY_ORC=1", self.navigation)
        self.assertIn("sudo systemctl stop docker", self.navigation)

    def test_linux_navigation_installs_built_map_renderer(self) -> None:
        self.assertIn(
            'sudo install -m 0755 "$renderer" '
            '"$INSTALL_ROOT/bin/openroadcode-map-renderer"',
            self.navigation,
        )

    def test_termux_navigation_always_rebuilds_and_installs_orc_renderer(self) -> None:
        self.assertIn(
            'cmake --build "$PROJECT_ROOT/apps/map_renderer/build-termux"',
            self.termux_navigation,
        )
        self.assertIn(
            'install -Dm755 "$MAP_RENDERER_BUILT" "$MAP_RENDERER_INSTALLED"',
            self.termux_navigation,
        )
        self.assertNotIn(
            'if should_build "$MAP_RENDERER_INSTALLED"; then',
            self.termux_navigation,
        )

    def test_sdrpp_feature_uses_orc_source_build_installer(self) -> None:
        self.assertIn(
            'bash "$SCRIPT_DIR/install_sdrpp_nightly.sh"',
            self.system_packages,
        )
        self.assertNotIn(
            "sudo apt install -y --no-install-recommends sdrpp",
            self.system_packages,
        )


if __name__ == "__main__":
    unittest.main()
