"""Exercise renderer sampling math when the optional Node test runner is available."""

from pathlib import Path
import shutil
import subprocess

import pytest


def test_terrain_interpolation_and_detail_limit():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is optional; terrain JS check requires node")
    test = Path(__file__).resolve().parents[3] / "frontends/web/cesium/unit_test/test_local_terrain.js"
    result = subprocess.run([node,"--test",str(test)],capture_output=True,text=True,timeout=20)
    assert result.returncode == 0, result.stdout+result.stderr


def test_camera_pitch_controls():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is optional; camera JS check requires node")
    test = Path(__file__).resolve().parents[3] / "frontends/web/cesium/unit_test/test_camera_controls.js"
    result = subprocess.run([node,"--test",str(test)],capture_output=True,text=True,timeout=20)
    assert result.returncode == 0, result.stdout+result.stderr
