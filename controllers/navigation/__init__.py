# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vehicle orientation and motion controller."""

from controllers.navigation.android_magnetometer_adapter import AndroidMagnetometerAdapter
from controllers.navigation.android_navigation_sensor import AndroidNavigationSensor
from controllers.navigation.browser_orientation_adapter import BrowserOrientationAdapter
from controllers.navigation.browser_position_adapter import BrowserPositionAdapter
from controllers.navigation.complementary_orientation_estimator import ComplementaryOrientationEstimator
from controllers.navigation.google_earth_map_presentation import GoogleEarthMapPresentation
from controllers.navigation.gpsd_navigation_adapter import GpsdNavigationAdapter
from controllers.navigation.gpsd_position_source import GpsdPositionSource
from controllers.navigation.magnetometer_source_if import MagnetometerSample, MagnetometerSourceIf
from controllers.navigation.map_presentation_if import MapPresentationIf
from controllers.navigation.mpu6050_navigation_adapter import Mpu6050NavigationAdapter
from controllers.navigation.motion_calibration import MotionCalibration
from controllers.navigation.navigation_controller import NavigationController
from controllers.navigation.navigation_controller_if import NavigationControllerIf
from controllers.navigation.navigation_controller_stub import NavigationControllerStub
from controllers.navigation.navigation_gps_source_if import NavigationGpsSourceIf
from controllers.navigation.navigation_sensor_if import MotionSample, NavigationSensorIf
from controllers.navigation.navigation_state import GpsState, NavigationState, OrientationState, PositionState
from controllers.navigation.navigation_state_presenter import NavigationStatePresenter
from controllers.navigation.position_source_if import PositionSourceIf
from controllers.navigation.position_snapshot_cache import PositionSnapshotCache
from controllers.navigation.persistent_position_source import PersistentPositionSource
from controllers.navigation.orientation_estimator_if import Orientation, OrientationEstimatorIf
from controllers.navigation.unconfigured_navigation_controller import UnconfiguredNavigationController
from controllers.navigation.simulated_navigation_controller import SimulatedNavigationController

__all__ = [
    "AndroidMagnetometerAdapter", "AndroidNavigationSensor", "BrowserOrientationAdapter", "BrowserPositionAdapter", "ComplementaryOrientationEstimator",
    "GoogleEarthMapPresentation", "GpsdNavigationAdapter", "GpsdPositionSource", "GpsState", "MagnetometerSample",
    "MagnetometerSourceIf", "MapPresentationIf", "MotionSample", "MotionCalibration", "Mpu6050NavigationAdapter",
    "NavigationController", "NavigationControllerIf", "NavigationControllerStub", "NavigationGpsSourceIf",
    "NavigationSensorIf", "NavigationState", "NavigationStatePresenter", "Orientation", "OrientationEstimatorIf",
    "OrientationState", "PositionSourceIf", "PositionSnapshotCache", "PositionState", "PersistentPositionSource",
    "SimulatedNavigationController", "UnconfiguredNavigationController",
]
