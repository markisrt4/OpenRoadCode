from config.radio_config_manager import (
    load_fm_radio_config,
    load_airband_am_config,
    load_weather_band_config,
    load_ham_radio_config,
)

from modules.radio.radio_controller import RadioController
from modules.radio.radio_types import RadioMode, RadioPreset, RadioRange

from modules.sdr.rigctl_client import RigctlClient
from modules.sdr.rigctl_backend import RigctlBackend
from modules.sdr.sdr_resource_manager import SDRResourceManager

from apps.launchers.sdrpp_launcher import (
    SDRPPLauncher,
    FM_BROADCAST_PROFILE,
    AIRBAND_AM_PROFILE,
    WEATHER_NOAA_PROFILE,
    HAM_RADIO_PROFILE,
)

from apps.launchers.adsb_launcher import ADSBLauncher
from apps.launchers.weather_dash_launcher import WeatherDashLauncher


def _build_radio_controller(
    radio_config,
    radio_range: RadioRange | None = None,
) -> RadioController:
    default_mode = RadioMode(
        name=radio_config.default_mode.name,
        bandwidth=radio_config.default_mode.bandwidth,
        step_hz=radio_config.default_mode.step_hz,
    )

    presets = [
        RadioPreset(
            label=preset.label,
            frequency_hz=preset.frequency_hz,
            mode=RadioMode(
                name=preset.mode.name,
                bandwidth=preset.mode.bandwidth,
                step_hz=preset.mode.step_hz,
            ),
        )
        for preset in radio_config.presets
    ]

    client = RigctlClient(host="127.0.0.1", port=4532)
    backend = RigctlBackend(client)

    return RadioController(
        backend=backend,
        presets=presets,
        default_mode=default_mode,
        radio_range=radio_range,
    )


def attach_radio_stacks(app) -> None:
    app.sdr_resource_manager = SDRResourceManager()

    app.fm_radio_config = load_fm_radio_config()
    app.fm_radio_controller = _build_radio_controller(
        app.fm_radio_config,
        RadioRange(
            min_frequency_hz=87_500_000,
            max_frequency_hz=108_000_000,
            start_frequency_hz=88_100_000,
        ),
    )
    app.fm_radio_launcher = SDRPPLauncher(FM_BROADCAST_PROFILE,
                                          resource_manager=app.sdr_resource_manager,
                                          owner_name="sdrpp_fm",
    )    

    app.airband_radio_config = load_airband_am_config()
    app.airband_radio_controller = _build_radio_controller(
        app.airband_radio_config,
        RadioRange(
            min_frequency_hz=118_000_000,
            max_frequency_hz=136_975_000,
            start_frequency_hz=125_000_000,
        ),
    )
    app.airband_radio_launcher = SDRPPLauncher(AIRBAND_AM_PROFILE,
                                               resource_manager=app.sdr_resource_manager,
    )

    app.weather_dash_launcher = WeatherDashLauncher()

    app.adsb_launcher = ADSBLauncher(
        url="http://127.0.0.1/tar1090",
        close_existing_display_apps=True,
    )

    app.weather_radio_config = load_weather_band_config()
    app.weather_radio_controller = _build_radio_controller(
        app.weather_radio_config,
        RadioRange(
            min_frequency_hz=162_400_000,
            max_frequency_hz=162_550_000,
            start_frequency_hz=162_550_000,
        ),
    )
    app.weather_radio_launcher = SDRPPLauncher(WEATHER_NOAA_PROFILE,
                                               resource_manager=app.sdr_resource_manager,
    )
    
    app.ham_radio_config = load_ham_radio_config()
    app.ham_radio_controller = _build_radio_controller(
        app.ham_radio_config,
        RadioRange(
            min_frequency_hz=144_000_000,
            max_frequency_hz=148_000_000,
            start_frequency_hz=146_520_000,
        ),
    )
    app.ham_radio_launcher = SDRPPLauncher(HAM_RADIO_PROFILE,
                                           resource_manager=app.sdr_resource_manager,
    )
