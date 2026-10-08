"""Feed navigation telemetry and semantic camera requests to Google Earth."""

import math
import threading
import time

from controllers.navigation.earth_geolocation_bridge import EarthGeolocationBridge
from controllers.navigation.earth_input_camera_controller import EarthInputCameraController
from controllers.navigation.earth_chase_camera_controller import EarthChaseCameraController
from messaging.contracts.navigation import (
    POSITION_STATE_TOPIC, MOTION_STATE_TOPIC, decode_position_state, decode_motion_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


class EarthNavigationController:
    """Own Earth GPS injection; browser operations run on the runtime worker."""

    def __init__(self, *, bridge=None, camera=None, dispatcher=None) -> None:
        self._bridge = bridge or EarthGeolocationBridge()
        self._camera = camera or EarthInputCameraController()
        self._chase = EarthChaseCameraController(self._camera)
        self._dispatcher = dispatcher or MessageDispatcher(ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT))
        self._dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, self._on_position)
        self._dispatcher.register(MOTION_STATE_TOPIC, decode_motion_state, self._on_motion)
        self._lock = threading.Lock()
        self._position = None
        self._motion = None
        self._follow = True
        self._tracking = False
        self._next_tracking_attempt = 0.0
        self._location_requested = False
        self.status = "Earth — waiting for ORC GPS"
        self._zoom = 16.5
        self._pitch = 0.0
        self._bearing = 0.0

    def start(self) -> None:
        self._dispatcher.start()

    def close(self) -> None:
        self._dispatcher.close()

    def reset(self) -> None:
        self._tracking = False
        self._next_tracking_attempt = 0.0
        self._location_requested = False
        self._follow = True
        self._chase.set_enabled(False)

    def _on_position(self, message) -> None:
        data = message.data
        with self._lock:
            self._position = data if data.latitude_rad is not None and data.longitude_rad is not None else None

    def _on_motion(self, message) -> None:
        with self._lock:
            self._motion = message.data

    def tick(self) -> bool:
        """Install the bridge after page load and deliver the latest valid fix."""
        if not self._bridge.install():
            self.status = "Earth — waiting for page and GPS bridge"
            return False
        with self._lock:
            position, motion = self._position, self._motion
        if position is None:
            self.status = "Earth — waiting for ORC GPS coordinates"
            return False
        if not self._follow:
            self.status = "Earth — location follow paused; use recenter"
            return True
        ok = self._bridge.push_position(
            math.degrees(position.latitude_rad), math.degrees(position.longitude_rad),
            altitude_m=position.altitude_m,
            accuracy_m=getattr(position, "accuracy_m", None) or 5.0,
            heading_deg=(math.degrees(motion.course_rad) if motion is not None
                         and motion.course_rad is not None else None),
            speed_m_s=motion.ground_speed_m_s if motion is not None else None,
        )
        if not ok:
            self._tracking = False
            self.status = "Earth — GPS bridge delivery failed; retrying"
            return False
        registrations = self._bridge.registration_count()
        self._tracking = self._location_requested and registrations is not None and registrations > 0
        now = time.monotonic()
        if not self._tracking and now >= self._next_tracking_attempt:
            self._location_requested = self._camera.activate_location_tracking()
            self._next_tracking_attempt = now + 5.0
        self.status = ("Earth — ORC GPS delivered" if self._tracking else
                       "Earth — GPS delivered; waiting for Earth's location control")
        return self._tracking

    def request_follow(self, enabled: bool) -> None:
        self._follow = enabled
        self._tracking = False
        self._next_tracking_attempt = 0.0
        self._location_requested = False
        if enabled:
            self.tick()

    def request_recenter(self) -> None:
        self.request_follow(True)

    def request_center_on(self, position) -> None:
        self._follow = False
        self._bridge.install()
        self._bridge.push_position(math.degrees(position.latitude_rad),
                                   math.degrees(position.longitude_rad), altitude_m=position.altitude_m)
        self._camera.activate_location_tracking()

    def request_pan_screen(self, right_px: float, up_px: float) -> None:
        self._follow = False
        self._camera.pan(right=right_px / 160.0, up=up_px / 160.0)

    def request_pan(self, north_m: float, east_m: float) -> None:
        self.request_pan_screen(east_m, north_m)

    def request_zoom(self, zoom_level: float) -> None:
        delta = zoom_level - self._zoom
        self._zoom = zoom_level
        if delta:
            (self._camera.zoom_in if delta > 0 else self._camera.zoom_out)()

    def request_pitch(self, pitch_rad: float) -> None:
        self._follow = False
        if pitch_rad == 0:
            self._camera.top_down()
        else:
            self._camera.tilt(math.degrees(pitch_rad - self._pitch))
        self._pitch = pitch_rad

    def request_bearing(self, bearing_rad: float) -> None:
        if bearing_rad == 0:
            self._camera.north_up()
        else:
            self._camera.rotate(math.degrees(bearing_rad - self._bearing))
        self._bearing = bearing_rad

    def request_chase(self, enabled: bool) -> None:
        """Select the branch's tested close oblique follow perspective."""
        self._chase.set_enabled(enabled)
        self.request_follow(enabled)
