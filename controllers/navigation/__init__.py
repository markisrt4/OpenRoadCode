# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vehicle orientation and motion controller."""

from importlib import import_module
from typing import Any

from controllers.navigation.complementary_orientation_estimator import ComplementaryOrientationEstimator
from controllers.navigation.magnetometer_source_if import MagnetometerSample, MagnetometerSourceIf
from controllers.navigation.map_presentation_if import MapPresentationIf
from controllers.navigation.motion_calibration import MotionCalibration
from controllers.navigation.navigation_controller import NavigationController
from controllers.navigation.navigation_controller_if import NavigationControllerIf
from controllers.navigation.navigation_controller_stub import NavigationControllerStub
from controllers.navigation.navigation_gps_source_if import NavigationGpsSourceIf
from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf
from controllers.navigation.navigation_state import GpsState, NavigationState, OrientationState, PositionState
from controllers.navigation.orientation_estimator_if import Orientation, OrientationEstimatorIf
from controllers.navigation.position_source_if import PositionSourceIf
from controllers.navigation.position_snapshot_cache import PositionSnapshotCache

__all__ = [
    "AndroidMagnetometerAdapter", "AndroidNavigationSensor", "BrowserOrientationAdapter", "BrowserPositionAdapter", "ComplementaryOrientationEstimator",
    "GoogleEarthMapPresentation", "GpsdNavigationAdapter", "GpsdPositionSource", "GpsState", "MagnetometerSample",
    "MagnetometerSourceIf", "MapPresentationIf", "MotionSample", "MotionCalibration", "Mpu6050NavigationAdapter",
    "NavigationController", "NavigationControllerIf", "NavigationControllerStub", "NavigationGpsSourceIf",
    "NavigationSensorIf", "NavigationState", "NavigationStatePresenter", "Orientation", "OrientationEstimatorIf",
    "OrientationState", "PositionSourceIf", "PositionSnapshotCache", "PositionState", "PersistentPositionSource",
    "SimulatedNavigationController", "UnconfiguredNavigationController",
]

_LAZY_EXPORTS = {
    "AndroidMagnetometerAdapter": ("controllers.navigation.android_magnetometer_adapter", "AndroidMagnetometerAdapter"),
    "AndroidNavigationSensor": ("controllers.navigation.android_navigation_sensor", "AndroidNavigationSensor"),
    "BrowserOrientationAdapter": ("controllers.navigation.browser_orientation_adapter", "BrowserOrientationAdapter"),
    "BrowserPositionAdapter": ("controllers.navigation.browser_position_adapter", "BrowserPositionAdapter"),
    "GoogleEarthMapPresentation": ("controllers.navigation.google_earth_map_presentation", "GoogleEarthMapPresentation"),
    "GpsdNavigationAdapter": ("controllers.navigation.gpsd_navigation_adapter", "GpsdNavigationAdapter"),
    "GpsdPositionSource": ("controllers.navigation.gpsd_position_source", "GpsdPositionSource"),
    "Mpu6050NavigationAdapter": ("controllers.navigation.mpu6050_navigation_adapter", "Mpu6050NavigationAdapter"),
    "NavigationStatePresenter": ("controllers.navigation.navigation_state_presenter", "NavigationStatePresenter"),
    "PersistentPositionSource": ("controllers.navigation.persistent_position_source", "PersistentPositionSource"),
    "SimulatedNavigationController": ("controllers.navigation.simulated_navigation_controller", "SimulatedNavigationController"),
    "UnconfiguredNavigationController": ("controllers.navigation.unconfigured_navigation_controller", "UnconfiguredNavigationController"),
}


def __getattr__(name: str) -> Any:
    """Load platform and presentation implementations only when requested."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
