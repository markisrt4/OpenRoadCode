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


def test_optional_terrain_cues_restore_globe_presentation():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is optional; terrain-cue JS check requires node")
    test = Path(__file__).resolve().parents[3] / "frontends/web/cesium/unit_test/test_terrain_cues.js"
    result = subprocess.run([node, "--test", str(test)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout+result.stderr


def test_bounded_local_terrain_hillshade():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is optional; terrain-hillshade JS check requires node")
    test = Path(__file__).resolve().parents[3] / "frontends/web/cesium/unit_test/test_terrain_hillshade.js"
    result = subprocess.run([node, "--test", str(test)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout+result.stderr


def test_building_relief_alignment():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is optional; building JS check requires node")
    test = Path(__file__).resolve().parents[3] / "frontends/web/cesium/unit_test/test_local_buildings.js"
    result = subprocess.run([node,"--test",str(test)],capture_output=True,text=True,timeout=20)
    assert result.returncode == 0, result.stdout+result.stderr


def test_vehicle_follow_and_fix_loss():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is optional; vehicle follow JS check requires node')
    test = Path(__file__).resolve().parents[3] / 'frontends/web/cesium/unit_test/test_vehicle_follow.js'
    result = subprocess.run([node,'--test',str(test)],capture_output=True,text=True,timeout=20)
    assert result.returncode == 0, result.stdout+result.stderr


def test_imagery_background_detail_and_late_load_cleanup():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is optional; imagery stack check requires node')
    test = Path(__file__).resolve().parents[3] / 'frontends/web/cesium/unit_test/test_local_imagery_layers.js'
    result = subprocess.run([node,'--test',str(test)],capture_output=True,text=True,timeout=20)
    assert result.returncode == 0, result.stdout+result.stderr


def test_road_overlay_labels_and_late_load_cleanup():
    node=shutil.which('node')
    if not node:
        pytest.skip('Node is optional; road overlay check requires node')
    test=Path(__file__).resolve().parents[3]/'frontends/web/cesium/unit_test/test_road_overlay.js'
    result=subprocess.run([node,'--test',str(test)],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr


def test_dynamic_poi_overlay_replaces_markers():
    node=shutil.which('node')
    if not node:
        pytest.skip('Node is optional; POI overlay check requires node')
    test=Path(__file__).resolve().parents[3]/'frontends/web/cesium/unit_test/test_poi_overlay.js'
    result=subprocess.run([node,'--test',str(test)],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr


def test_dynamic_route_overlay_replaces_route():
    node=shutil.which('node')
    if not node:
        pytest.skip('Node is optional; route overlay check requires node')
    test=Path(__file__).resolve().parents[3]/'frontends/web/cesium/unit_test/test_route_overlay.js'
    result=subprocess.run([node,'--test',str(test)],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
