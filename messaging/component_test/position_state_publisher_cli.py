# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publish simulated navigation positions using the public contract."""

import math
import time
from datetime import datetime, timezone

from controllers.navigation.navigation_state import PositionState
from messaging.contracts.navigation import PositionStatePublisher
from messaging.zeromq import ZeroMqPublisher


def main() -> None:
    publisher = ZeroMqPublisher()
    position_publisher = PositionStatePublisher(publisher)
    phase = 0.0
    try:
        while True:
            state = PositionState(
                received_at=datetime.now(timezone.utc),
                latitude_deg=42.8028 + 0.001 * math.sin(phase),
                longitude_deg=-83.0127 + 0.001 * math.cos(phase),
                altitude_m=250.0 + 2.0 * math.sin(phase / 2.0),
                speed_mps=13.4 + 1.5 * math.sin(phase),
                course_deg=(90.0 + math.degrees(phase)) % 360.0,
                fix_mode=3,
                satellites_visible=14,
                satellites_used=10,
                accuracy_m=2.5,
                source="simulator",
                is_cached=False,
            )
            position_publisher.publish(state)
            phase += 0.05
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
