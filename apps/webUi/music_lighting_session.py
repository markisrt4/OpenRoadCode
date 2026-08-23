# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Web transport adapter for the shared MusicLightingController."""
from __future__ import annotations

from controllers.music_lighting import MusicLightingController, MusicLightingPatternId


class WebMusicLightingSession:
    def __init__(self, controller: MusicLightingController) -> None:
        self.controller = controller

    def state(self) -> dict[str, object]:
        state = self.controller.state
        return {
            "enabled": state.enabled,
            "pattern": state.pattern.value,
            "intensity": state.intensity,
            "brightness_limit": state.brightness_limit,
        }

    def command(self, command: str, value: object = None) -> dict[str, object]:
        command = command.strip().lower()
        if command == "enabled":
            self.controller.request_enabled(bool(value))
        elif command == "pattern":
            self.controller.request_pattern(MusicLightingPatternId(str(value)))
        elif command == "intensity":
            self.controller.request_intensity(float(value))
        elif command == "brightness_limit":
            self.controller.request_brightness_limit(int(value))
        else:
            raise ValueError(f"Unknown music lighting command: {command}")
        return self.state()
