# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import os
from pathlib import Path
import subprocess

import pytest


HELPER = Path(__file__).resolve().parents[2] / "development/termux/maplibre_build_state.sh"


@pytest.mark.parametrize(
    ("stamp", "artifact", "cache", "force", "expected"),
    [
        (None, True, True, "0", 0),
        ("libpng=1.6.58", True, True, "0", 0),
        ("libpng=1.6.59", True, True, "0", 1),
        ("libpng=1.6.59", False, True, "0", 0),
        ("libpng=1.6.59", True, False, "0", 0),
        ("libpng=1.6.59", True, True, "1", 0),
    ],
)
def test_maplibre_rebuild_after_package_upgrade(tmp_path, stamp, artifact, cache, force, expected):
    if artifact:
        (tmp_path / "mbgl-glfw").touch()
    if cache:
        (tmp_path / "CMakeCache.txt").touch()
    if stamp is not None:
        (tmp_path / "stamp").write_text(stamp + "\n")
    result = subprocess.run(
        [
            "bash", "-c",
            'source "$1"; maplibre_needs_build "$2/mbgl-glfw" "$2" "$2/stamp" "libpng=1.6.59"',
            "test", str(HELPER), str(tmp_path),
        ],
        env={**os.environ, "FORCE_REBUILD": force},
        check=False,
    )
    assert result.returncode == expected


def test_signature_tracks_png_headers_and_package_version(tmp_path):
    include = tmp_path / "include"
    include.mkdir()
    for name in ("png.h", "pngconf.h"):
        (include / name).write_text("old header")
    command = [
        "bash", "-c",
        'source "$1"; pkg-config() { echo "$PNG_VERSION"; }; maplibre_build_signature',
        "test", str(HELPER),
    ]
    env = {**os.environ, "PREFIX": str(tmp_path), "MAPLIBRE_REF": "pinned", "PNG_VERSION": "1.6.58"}
    before = subprocess.check_output(command, env=env)
    env["PNG_VERSION"] = "1.6.59"
    upgraded = subprocess.check_output(command, env=env)
    assert before != upgraded
    (include / "png.h").write_text("new header")
    assert subprocess.check_output(command, env=env) != upgraded
