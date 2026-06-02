from typing import Callable
from pathlib import Path

from apps.carUi.sdrControlPanel import SDRControlPanel
from apps.carUi.config.radio_manifest_parser import RadioManifestParser
from apps.carUi.radio_runtime_assembly import assemble_radio_runtime
from modules.gps.gps_device import GPSDevice


def make_on_fm_radio(app: SDRControlPanel) -> Callable[[str], None]:
    def on_fm_radio(component: str) -> None:
        print(f"Opening {component}: FM radio panel")
        app.fm_keyboard_adapter.connect()
        app.show_fm_radio_menu()

    return on_fm_radio

def make_on_scanner_radio(app: SDRControlPanel) -> Callable[[str], None]:
    def on_scanner_radio(component: str) -> None:
        #app. connect
        print(f"Launching {component}: open scanner radio controls")
        app.show_scanner_radio_menu()

    return on_scanner_radio


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

    gps_device = GPSDevice()
    gps_device.start()

    app = SDRControlPanel(remote_display=":2")
    app.gps_device = gps_device
    app.start_gps_ui_updates()

    radio_manifest_parser = RadioManifestParser(Path("apps/carUi/config/radio_manifest.json"))

    assemble_radio_runtime(app, radio_manifest_parser=radio_manifest_parser)

    app.callbacks.update({
        "fm_radio":      lambda key: app.show_fm_radio_menu(),
        "scanner_radio": lambda key: app.show_scanner_radio_menu(),
        "aircraft":      lambda key: app.show_aircraft_menu(),
        "lighting": on_lighting,
        "weather":       lambda key: app.show_weather_menu(),
        "settings":      lambda key: app.show_settings_menu(),
    })

    app.mainloop()