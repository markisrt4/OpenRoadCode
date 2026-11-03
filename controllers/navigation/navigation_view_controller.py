# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from ui.navigation.navigation_view_if import NavigationViewState


class NavigationViewController:
    def __init__(self, *, open_map, open_waze):
        self._open_map, self._open_waze = open_map, open_waze
        self._state = NavigationViewState()

    @property
    def state(self):
        return self._state

    def remember_map(self):
        self._state = NavigationViewState('map')

    def remember_waze(self):
        self._state = NavigationViewState('waze')

    def request_resume_navigation(self):
        (self._open_waze if self._state.selected == 'waze' else self._open_map)()
