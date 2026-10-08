# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Headless radar presentation with the same contract as the navigation view."""

from ui.weather.radar_ui_if import RadarUiIf, RadarUiState


class RadarUiStub(RadarUiIf):
    def __init__(self):
        self.state = RadarUiState()

    def set_radar_state(self, state):
        self.state = state
