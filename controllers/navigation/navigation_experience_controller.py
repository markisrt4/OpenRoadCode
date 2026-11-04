"""Route shared navigation actions without coupling the views to runtimes."""
from ui.navigation.navigation_experience_if import NavigationExperience, NavigationExperienceState
from ui.navigation.map_platform_if import MapPlatform
from ui.navigation.poi_models import TransitMode


class NavigationExperienceController:
    def __init__(self, *, platform, navigation_state, open_map, open_waze,
                 waze_state, waze_available, saved_map, saved_waze,
                 show_places, search_places, select_place, clear_places, close_waze, select_platform=None):
        self._platform = platform
        self._navigation_state = navigation_state
        self._open_map, self._open_waze = open_map, open_waze
        self._waze_state, self._waze_available = waze_state, waze_available
        self._saved_map, self._saved_waze = saved_map, saved_waze
        self._show_places, self._search_places = show_places, search_places
        self._select_place, self._clear_places = select_place, clear_places
        self._close_waze = close_waze
        self._select_platform = select_platform or platform.request_platform

    @property
    def state(self):
        platform = self._platform.state
        waze = self._waze_state()
        selected = (NavigationExperience.WAZE if self._navigation_state().selected == 'waze'
                    else NavigationExperience.TERRAIN if platform.requested is MapPlatform.CESIUM
                    else NavigationExperience.ROAD)
        return NavigationExperienceState(selected=selected,
            terrain_available=MapPlatform.CESIUM in platform.available_platforms,
            waze_available=self._waze_available(), waze_running=waze.active,
            busy=platform.busy or waze.launching or waze.closing)

    def request_experience(self, experience):
        if self.state.busy:
            return
        if experience is NavigationExperience.WAZE:
            if self.state.waze_available:
                self._open_waze()
            return
        if experience is NavigationExperience.TERRAIN and not self.state.terrain_available:
            return
        if self._navigation_state().selected == 'waze':
            self._open_map()
        target = MapPlatform.CESIUM if experience is NavigationExperience.TERRAIN else MapPlatform.MAPLIBRE
        if self._platform.state.requested is not target:
            self._select_platform(target)

    def request_saved_destination(self, key):
        if key not in ('home', 'work'):
            return
        (self._saved_waze if self.state.selected is NavigationExperience.WAZE else self._saved_map)(key)

    def request_places(self):
        if self._navigation_state().selected == 'waze':
            self._open_map()
        self._show_places()

    def request_search_places(self, category, transit=TransitMode.ALL):
        if self._navigation_state().selected == 'waze':
            self._open_map()
        self._search_places(category, transit)

    def request_select_place(self, place):
        self._select_place(place)

    def request_clear_places(self):
        self._clear_places()

    def request_close_waze(self):
        self._close_waze()
