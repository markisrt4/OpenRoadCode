"""Resolve the separately installed, pinned Cesium browser distribution."""

from common.xdg_paths import openroadcode_data_dir

VERSION = "1.124.0"
TARBALL = f"https://registry.npmjs.org/cesium/-/cesium-{VERSION}.tgz"
INTEGRITY = "sha512-FDfjr7sWLeYkrblW50KXXbe2vsLuKmY6BY/gFDCjntQBdmQs0uWuOhtM0rW+V4510IgqQj4MYLK8CHOOChvA8w=="


def sdk_directory():
    return openroadcode_data_dir("cesium", VERSION, "Build", "Cesium")


def require_sdk(directory):
    """Fail early instead of silently falling back to a remote CDN."""
    for name in ("Cesium.js", "Widgets/widgets.css", "Assets", "Workers"):
        if not (directory / name).exists():
            raise RuntimeError("Cesium SDK is missing; run python -m development.maps.install_cesium")
    return directory.resolve()
