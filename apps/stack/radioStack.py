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
                                               owner_name="sdrpp_airband",
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
                                               owner_name="sdrpp_weather",
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
                                           owner_name="sdrpp_ham", 
    )

    app.start_fm_radio = lambda: ensure_radio_profile(
        app,
        app.fm_radio_launcher,
        app.fm_radio_controller,
        FM_BROADCAST_PROFILE,
        app.remote_display,
    )

    app.start_airband_radio = lambda: ensure_radio_profile(
        app,
        app.airband_radio_launcher,
        app.airband_radio_controller,
        AIRBAND_AM_PROFILE,
        app.remote_display,
    )

    app.start_weather_radio = lambda: ensure_radio_profile(
        app,
        app.weather_radio_launcher,
        app.weather_radio_controller,
        WEATHER_NOAA_PROFILE,
        app.remote_display,
    )

    app.start_ham_radio = lambda: ensure_radio_profile(
        app,
        app.ham_radio_launcher,
        app.ham_radio_controller,
        HAM_RADIO_PROFILE,
        app.remote_display,
    )

def ensure_radio_profile(
    app,
    launcher,
    controller,
    profile,
    remote_display: str = ":2",
) -> None:
    """
    Make sure SDR++ is running, rigctl is ready, and the active radio profile
    has the correct mode/frequency for the selected panel.
    """
    set_status = app.status_var.set

    launcher.launch(
        remote_display=remote_display,
        set_status=set_status,
    )

    # Force mode first, then frequency.
    # SDR++ can come up with whatever it last used, because naturally it remembers
    # the one thing we do not want it to trust blindly.
    mode = controller.default_mode
    controller.set_mode(mode)

    frequency_hz = profile.start_frequency_hz
    if frequency_hz is not None:
        controller.set_frequency(frequency_hz)
        app.set_current_frequency(frequency_hz)

    controller.start()
    controller.set_mode(mode)

    set_status(
        f"{profile.name} ready: {mode.name}, "
        f"{frequency_hz / 1_000_000:.3f} MHz"
        if frequency_hz is not None
        else f"{profile.name} ready: {mode.name}"
    )
