"""Aircraft controller and deterministic simulation tests."""

from controllers.adsb.aircraft_overlay_controller import AircraftOverlayController
from ui.adsb.aircraft_overlay_state import AircraftPoint
from ui.navigation.map_ui_if import GeoPoint


def simulated_aircraft(elapsed_s, count):
    return tuple(
        AircraftPoint(f"{0xA00000 + i:06X}", GeoPoint(elapsed_s / 1000, i / 1000))
        for i in range(count)
    )


class View:
    def __init__(self):
        self.states = []

    def set_aircraft_overlay_state(self, state):
        self.states.append(state)


def test_simulation_is_deterministic_and_moves():
    assert simulated_aircraft(0, 3) == simulated_aircraft(0, 3)
    assert simulated_aircraft(1, 3) != simulated_aircraft(0, 3)


def test_selection_follow_and_expiry():
    view = View()
    controller = AircraftOverlayController(view)
    controller.set_aircraft(simulated_aircraft(0, 2))
    icao = controller.state.aircraft[0].icao
    controller.request_aircraft_selection(icao.lower())
    controller.request_aircraft_follow(icao)
    assert controller.state.selected_icao == icao
    assert controller.state.follow_icao == icao
    controller.set_aircraft(())
    assert controller.state.selected_icao is None
    assert controller.state.follow_icao is None


def test_visibility_and_replay():
    view = View()
    controller = AircraftOverlayController(view)
    controller.request_aircraft_visible(False)
    assert not controller.state.enabled
    count = len(view.states)
    controller.request_aircraft_replay()
    assert len(view.states) == count + 1
    assert view.states[-1] == view.states[-2]
