# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Platform defaults and explicit camera selection are composition decisions."""

from unittest.mock import patch
from unittest.mock import Mock
import pytest
from apps.orcUi.composition.vision_camera import create_vision_camera
from hardware_io.camera.android_bridge_camera import AndroidBridgeCamera
from hardware_io.camera.v4l2_camera import V4L2Camera
from hardware_io.camera.software_camera_controls import SoftwareCameraControls


def test_termux_defaults_to_the_bridge_without_opening_it():
    camera, controls, label = create_vision_camera({'PREFIX': '/data/data/com.termux/files/usr'})
    assert isinstance(camera, AndroidBridgeCamera)
    assert isinstance(controls, SoftwareCameraControls)
    assert not camera.is_open and label == 'Android Bridge camera'


def test_desktop_keeps_v4l2_and_explicit_device_selection():
    camera, _, label = create_vision_camera({'OPENROADCODE_VISION_CAMERA_DEVICE': '/dev/video2'})
    assert isinstance(camera, V4L2Camera)
    assert camera.device == label == '/dev/video2'


def test_explicit_bridge_can_be_used_from_a_remote_linux_runtime():
    with patch('apps.orcUi.composition.vision_camera.AndroidBridgeCamera') as factory:
        create_vision_camera({'OPENROADCODE_VISION_CAMERA_SOURCE': 'android_bridge',
                              'OPENROADCODE_VISION_BRIDGE_URL': 'http://phone:8767'})
        factory.assert_called_once_with('http://phone:8767')


def test_bad_source_is_rejected_before_any_device_is_opened():
    with pytest.raises(ValueError, match='android_bridge or v4l2'):
        create_vision_camera({'OPENROADCODE_VISION_CAMERA_SOURCE': 'unknown'})


def test_termux_composition_wires_bridge_frames_into_existing_vision_controller():
    from apps.orcUi.composition.vision import configure_vision
    with patch.dict('os.environ', {'PREFIX': '/data/data/com.termux/files/usr'}, clear=True), \
            patch('apps.orcUi.composition.vision.CameraVisionScreen'), \
            patch('apps.orcUi.composition.vision.YoloModelReadiness'), \
            patch('apps.orcUi.composition.vision.LazyYoloObjectDetector'), \
            patch('apps.orcUi.composition.vision.ByteTrackObjectTracker'), \
            patch('apps.orcUi.composition.vision.VisionController') as controller:
        composition = configure_vision(Mock())
        camera, controls = controller.call_args.args[2:4]
        assert isinstance(camera, AndroidBridgeCamera)
        assert isinstance(controls, SoftwareCameraControls)
        assert controller.call_args.kwargs['source_label'] == 'Android Bridge camera'
        assert not camera.is_open
        composition.close()
