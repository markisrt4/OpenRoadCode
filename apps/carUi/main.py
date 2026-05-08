from typing import Callable
from .sdrControlPanel import SDRControlPanel
from ..stack.radioStack import attach_radio_stacks
#from modules.gps.gps_device import GPSDevice


def make_on_fm_radio(app: SDRControlPanel) -> Callable[[str], None]:
    def on_fm_radio(component: str) -> None:
        print(f"Opening {component}: FM radio panel")
        app.fm_keyboard_adapter.connect()
        app.show_fm_radio_menu()

    return on_fm_radio


def on_ham_radio(component: str) -> None:
    print(f"Launching {component}: open ham/CB radio controls")


def make_on_aircraft(app: SDRControlPanel) -> Callable[[str], None]:
    def on_aircraft(component: str) -> None:
        print(f"Opening {component}: aircraft submenu")
        app.show_aircraft_menu()

    return on_aircraft


def on_lighting(component: str) -> None:
    print(f"Launching {component}: open LED lighting controls")


def make_on_weather(app: SDRControlPanel) -> Callable[[str], None]:
    def on_weather(component: str) -> None:
        print(f"Opening {component}: weather panel")
        app.show_weather_menu()

    return on_weather


def on_settings(component: str) -> None:
    print(f"Launching {component}: open settings page")


if __name__ == "__main__":

    #gps_device = GPSDevice()
    #gps_device.start()

    app = SDRControlPanel(remote_display=":2")

    attach_radio_stacks(app)

    app.callbacks.update({
        "fm_radio": lambda key: app.fm_radio_panel_manager.show(),
        "ham_radio": lambda key: app.ham_radio_panel_manager.show(),
        "aircraft": lambda key: app.aircraft_panel_manager.show(),
        "lighting": on_lighting,
        "weather": lambda key: app.weather_panel_manager.show(),
        "settings": on_settings,
    })

    app.mainloop()