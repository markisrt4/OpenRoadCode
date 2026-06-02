from __future__ import annotations

from pathlib import Path
from typing import Optional

from config.radio_config_manager import load_radio_config

from apps.launchers.adsb_launcher import ADSBLauncher
from apps.launchers.sdrpp_launcher import SDRPPLauncher, SDRPPProfile
from apps.launchers.weather_dash_launcher import WeatherDashLauncher

from modules.radio.radio_controller import RadioController
from modules.radio.radio_types import RadioMode, RadioPreset, RadioRange

from modules.sdr.rigctl_backend import RigctlBackend
from modules.sdr.rigctl_client import RigctlClient
from modules.sdr.sdr_resource_manager import SDRResourceManager


def assemble_radio_runtime(app, radio_manifest_parser=None) -> None:
    """
    Build and attach the CarSDR radio runtime objects.

    This function intentionally handles assembly/glue only:
      - load config files selected by the manifest
      - create RadioController instances
      - create SDR++ launchers
      - attach predictable attributes/callbacks onto the app

    Frequency ranges belong in the JSON config files, not here.
    """
    app.sdr_resource_manager = SDRResourceManager()

    manifest = _load_manifest_or_raise(radio_manifest_parser)

    for entry in manifest.radio_configs:
        _assemble_named_radio(app, attr_prefix=entry.key, config_path=entry.config_path)

    for entry in manifest.scanner_bands:
        _assemble_named_radio(app, attr_prefix=entry.key, config_path=entry.config_path)

    _assemble_auxiliary_launchers(app)


def _load_manifest_or_raise(radio_manifest_parser):
    if radio_manifest_parser is None:
        raise ValueError(
            "assemble_radio_runtime() requires a radio_manifest_parser. "
            "Create RadioManifestParser in main.py and pass it in."
        )

    return radio_manifest_parser.load()


def _assemble_named_radio(
    app,
    attr_prefix: str,
    config_path: str | Path,
) -> None:
    """
    Assemble one configured radio service as:

      app.<attr_prefix>_config
      app.<attr_prefix>_controller
      app.<attr_prefix>_launcher
      app.start_<attr_prefix>_radio

    Examples:
      app.fm_radio_config
      app.fm_radio_controller
      app.fm_radio_launcher
      app.start_fm_radio_radio

    Compatibility aliases are added for existing FM/Airband/Weather call sites.
    """
    config = load_radio_config(config_path)

    controller = _build_radio_controller(config)
    profile = _build_profile(config, fallback_name=config.label)
    launcher = _build_sdrpp_launcher(
        profile=profile,
        resource_manager=app.sdr_resource_manager,
        owner_name=f"sdrpp_{attr_prefix}",
    )

    setattr(app, f"{attr_prefix}_config", config)
    setattr(app, f"{attr_prefix}_controller", controller)
    setattr(app, f"{attr_prefix}_launcher", launcher)

    setattr(
        app,
        f"start_{attr_prefix}_radio",
        lambda launcher=launcher, controller=controller, profile=profile: ensure_radio_profile(
            app,
            launcher,
            controller,
            profile,
            app.remote_display,
        ),
    )

    _add_legacy_aliases(app, attr_prefix)


def _add_legacy_aliases(app, attr_prefix: str) -> None:
    """
    Preserve existing code expectations while the app migrates to manifest-driven names.

    Current panel managers expect:
      fm_radio_*
      airband_radio_*
      weather_radio_*

    ScannerPanelManager expects scanner band names directly.
    """
    if attr_prefix in {"fm_radio", "airband_radio", "weather_radio"}:
        return

    if attr_prefix == "airband":
        _alias_radio_attrs(app, source_prefix="airband", alias_prefix="airband_radio")

    if attr_prefix == "weather_band":
        _alias_radio_attrs(app, source_prefix="weather_band", alias_prefix="weather_radio")


def _alias_radio_attrs(app, source_prefix: str, alias_prefix: str) -> None:
    for suffix in ("config", "controller", "launcher"):
        setattr(
            app,
            f"{alias_prefix}_{suffix}",
            getattr(app, f"{source_prefix}_{suffix}"),
        )

    setattr(
        app,
        f"start_{alias_prefix}_radio",
        getattr(app, f"start_{source_prefix}_radio"),
    )


def _assemble_auxiliary_launchers(app) -> None:
    app.weather_dash_launcher = WeatherDashLauncher()

    app.adsb_launcher = ADSBLauncher(
        url="http://127.0.0.1/tar1090",
        close_existing_display_apps=True,
    )


def _build_radio_controller(radio_config) -> RadioController:
    default_mode = _runtime_mode(radio_config.default_mode)

    presets = [
        RadioPreset(
            label=preset.label,
            frequency_hz=preset.frequency_hz,
            mode=_runtime_mode(preset.mode),
        )
        for preset in radio_config.presets
    ]

    client = RigctlClient(host="127.0.0.1", port=4532)
    backend = RigctlBackend(client)

    return RadioController(
        backend=backend,
        presets=presets,
        default_mode=default_mode,
        radio_range=_runtime_range(radio_config),
    )


def _runtime_mode(mode_config) -> RadioMode:
    return RadioMode(
        name=mode_config.name,
        bandwidth=mode_config.bandwidth,
        step_hz=mode_config.step_hz,
    )


def _runtime_range(radio_config) -> RadioRange | None:
    radio_range = getattr(radio_config, "radio_range", None)
    if radio_range is None:
        return _derive_range_from_presets(radio_config)

    return RadioRange(
        min_frequency_hz=radio_range.min_frequency_hz,
        max_frequency_hz=radio_range.max_frequency_hz,
        start_frequency_hz=radio_range.start_frequency_hz,
    )


def _derive_range_from_presets(radio_config) -> RadioRange | None:
    """
    Fallback only.

    Prefer explicit JSON "range" blocks. This keeps the app from crashing if a
    config is missing a range, but it should not become the normal path.
    """
    presets = getattr(radio_config, "presets", [])
    if not presets:
        return None

    freqs = [preset.frequency_hz for preset in presets]

    return RadioRange(
        min_frequency_hz=min(freqs),
        max_frequency_hz=max(freqs),
        start_frequency_hz=freqs[0],
    )


def _profile_start_frequency(radio_config) -> Optional[int]:
    radio_range = _runtime_range(radio_config)
    if radio_range is not None:
        return radio_range.start_frequency_hz

    presets = getattr(radio_config, "presets", [])
    if presets:
        return presets[0].frequency_hz

    return None


def _build_profile(
    radio_config,
    fallback_name: str,
) -> SDRPPProfile:
    return SDRPPProfile(
        name=getattr(radio_config, "label", fallback_name),
        mode=radio_config.default_mode.name,
        step_hz=radio_config.default_mode.step_hz,
        start_frequency_hz=_profile_start_frequency(radio_config),
    )


def _build_sdrpp_launcher(
    profile: SDRPPProfile,
    resource_manager: SDRResourceManager,
    owner_name: str,
) -> SDRPPLauncher:
    return SDRPPLauncher(
        profile=profile,
        resource_manager=resource_manager,
        owner_name=owner_name,
    )


def _force_controller_mode(controller: RadioController) -> None:
    mode = controller.default_mode
    controller.backend.set_mode(mode.name, mode.bandwidth)


def _force_controller_frequency(
    controller: RadioController,
    frequency_hz: Optional[int],
) -> Optional[int]:
    if frequency_hz is None:
        return None

    controller.set_frequency(frequency_hz)
    return frequency_hz


def ensure_radio_profile(
    app,
    launcher: SDRPPLauncher,
    controller: RadioController,
    profile: SDRPPProfile,
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

    # SDR++ can finish launching, restore old state, then accept commands.
    # Reasserting mode/frequency before and after start is intentionally
    # redundant. The machine can cope.
    _force_controller_mode(controller)

    frequency_hz = profile.start_frequency_hz
    tuned_frequency_hz = _force_controller_frequency(controller, frequency_hz)
    if tuned_frequency_hz is not None:
        app.set_current_frequency(tuned_frequency_hz)

    controller.start()

    _force_controller_mode(controller)
    tuned_frequency_hz = _force_controller_frequency(controller, frequency_hz)
    if tuned_frequency_hz is not None:
        app.set_current_frequency(tuned_frequency_hz)

    mode = controller.default_mode
    set_status(
        f"{profile.name} ready: {mode.name}, "
        f"{tuned_frequency_hz / 1_000_000:.3f} MHz"
        if tuned_frequency_hz is not None
        else f"{profile.name} ready: {mode.name}"
    )
