from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


DEFAULT_RADIO_CONFIG_DIR = Path("config/radio")


class CarUiRuntimeConfigError(ValueError):
    """Raised when the Car UI runtime TOML file is invalid."""


@dataclass(frozen=True, slots=True)
class RuntimeDisplayConfig:
    """Configure the X display used by externally launched applications."""
    remote_display: str = ":2"


@dataclass(frozen=True, slots=True)
class RigctlConfig:
    """Configure the host and TCP port of the rigctl service."""
    host: str = "127.0.0.1"
    port: int = 4532


@dataclass(frozen=True, slots=True)
class SeesawEncoderConfig:
    """Configure one I2C Seesaw rotary encoder."""
    address: int
    reverse_direction: bool = False


@dataclass(frozen=True, slots=True)
class GpioEncoderConfig:
    """Configure one GPIO rotary encoder and its optional button."""
    pin_a: int
    pin_b: int
    button: int | None = None
    reverse_direction: bool = False


EncoderDeviceConfig = SeesawEncoderConfig | GpioEncoderConfig


@dataclass(frozen=True, slots=True)
class RotaryEncoderConfig:
    """Configure the ordered encoder devices and designated volume encoder."""
    devices: tuple[EncoderDeviceConfig, ...] = (
        SeesawEncoderConfig(address=0x36),
        SeesawEncoderConfig(address=0x37),
        SeesawEncoderConfig(address=0x38),
    )
    volume_index: int = 0

    @property
    def panel_count(self) -> int:
        """Return the number of encoders available for panel-specific input."""
        return len(self.devices) - 1


@dataclass(frozen=True, slots=True)
class InputConfig:
    """Contain runtime configuration for Car UI input devices."""
    rotary_encoders: RotaryEncoderConfig


@dataclass(frozen=True, slots=True)
class RadioStackConfig:
    """Configure one radio backend, profile, and optional launcher."""
    key: str
    config_path: Path
    backend: str
    launcher: str | None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class AdsbConfig:
    """Configure the auxiliary ADS-B browser application."""
    enabled: bool = True
    url: str = "http://127.0.0.1/tar1090"
    close_existing_display_apps: bool = True


@dataclass(frozen=True, slots=True)
class WeatherDashboardConfig:
    """Configure availability of the auxiliary weather dashboard."""
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class AuxiliaryConfig:
    """Contain optional applications launched by the Car UI."""
    adsb: AdsbConfig
    weather_dashboard: WeatherDashboardConfig


@dataclass(frozen=True, slots=True)
class CarUiRuntimeConfig:
    """Contain the validated runtime composition of the Car UI."""
    runtime: RuntimeDisplayConfig
    rigctl: RigctlConfig
    input: InputConfig
    radios: tuple[RadioStackConfig, ...]
    auxiliary: AuxiliaryConfig

    def enabled_radios(self) -> tuple[RadioStackConfig, ...]:
        """Return radio stacks enabled in this configuration."""
        return tuple(radio for radio in self.radios if radio.enabled)

    def radio(self, key: str) -> RadioStackConfig:
        """Return a radio stack by key.

        @param key Stable radio-stack identifier.
        @raises KeyError if the key is not configured.
        """
        for radio in self.radios:
            if radio.key == key:
                return radio
        raise KeyError(f"Unknown radio stack: {key}")


class CarUiRuntimeConfigParser:
    """
    Parse the Car UI runtime composition TOML file.

    Runtime composition belongs here. Radio-domain settings such as presets,
    frequency ranges, modes, bandwidths, and tuning steps remain in the JSON
    files under PROJECT_ROOT/config/radio.
    """

    def __init__(
        self,
        config_path: str | Path,
        *,
        project_root: str | Path | None = None,
        require_radio_files: bool = True,
    ) -> None:
        self.config_path = Path(config_path).expanduser().resolve()
        self.project_root = (
            Path(project_root).expanduser().resolve()
            if project_root is not None
            else self._default_project_root()
        )
        self.radio_config_dir = self.project_root / DEFAULT_RADIO_CONFIG_DIR
        self.require_radio_files = require_radio_files

    def load(self) -> CarUiRuntimeConfig:
        """Load and validate the configured TOML file.

        @return Validated Car UI runtime configuration.
        @raises CarUiRuntimeConfigError if the file is missing or invalid.
        """
        try:
            with self.config_path.open("rb") as file:
                data = tomllib.load(file)
        except FileNotFoundError as exc:
            raise CarUiRuntimeConfigError(
                f"Runtime config file not found: {self.config_path}"
            ) from exc
        except tomllib.TOMLDecodeError as exc:
            raise CarUiRuntimeConfigError(
                f"Invalid TOML in {self.config_path}: {exc}"
            ) from exc

        runtime = self._parse_runtime(data.get("runtime", {}))
        rigctl = self._parse_rigctl(data.get("rigctl", {}))
        input_config = self._parse_input(data.get("input", {}))
        radios = self._parse_radios(data.get("radios", []))
        auxiliary = self._parse_auxiliary(data.get("auxiliary", {}))

        return CarUiRuntimeConfig(
            runtime=runtime,
            rigctl=rigctl,
            input=input_config,
            radios=radios,
            auxiliary=auxiliary,
        )

    def _parse_runtime(self, data: Any) -> RuntimeDisplayConfig:
        section = self._expect_table(data, "runtime")
        remote_display = self._optional_string(
            section,
            "remote_display",
            default=":2",
            section_name="runtime",
        )
        return RuntimeDisplayConfig(remote_display=remote_display)

    def _parse_rigctl(self, data: Any) -> RigctlConfig:
        section = self._expect_table(data, "rigctl")
        host = self._optional_string(
            section,
            "host",
            default="127.0.0.1",
            section_name="rigctl",
        )
        port = section.get("port", 4532)

        if not isinstance(port, int) or isinstance(port, bool):
            raise CarUiRuntimeConfigError("rigctl.port must be an integer")
        if not 1 <= port <= 65535:
            raise CarUiRuntimeConfigError(
                "rigctl.port must be between 1 and 65535"
            )

        return RigctlConfig(host=host, port=port)

    def _parse_input(self, data: Any) -> InputConfig:
        section = self._expect_table(data, "input")
        encoder_data = self._expect_table(
            section.get("rotary_encoders", {}),
            "input.rotary_encoders",
        )

        devices_data = encoder_data.get("devices")
        devices = (
            self._default_encoder_devices()
            if devices_data is None
            else self._parse_encoder_devices(devices_data)
        )
        volume_index = encoder_data.get("volume_index", 0)
        if (
            not isinstance(volume_index, int)
            or isinstance(volume_index, bool)
            or not 0 <= volume_index < len(devices)
        ):
            raise CarUiRuntimeConfigError(
                "input.rotary_encoders.volume_index must identify a "
                "configured encoder"
            )

        return InputConfig(
            rotary_encoders=RotaryEncoderConfig(
                devices=devices,
                volume_index=volume_index,
            )
        )

    def _parse_encoder_devices(
        self,
        data: Any,
    ) -> tuple[EncoderDeviceConfig, ...]:
        if not isinstance(data, list) or not data:
            raise CarUiRuntimeConfigError(
                "input.rotary_encoders.devices must be a non-empty "
                "array of tables"
            )

        devices: list[EncoderDeviceConfig] = []
        seesaw_addresses: set[int] = set()
        gpio_pins: set[int] = set()

        for index, item in enumerate(data):
            section_name = f"input.rotary_encoders.devices[{index}]"
            section = self._expect_table(item, section_name)
            driver = self._required_string(section, "driver", section_name)
            reverse_direction = self._optional_bool(
                section,
                "reverse_direction",
                default=False,
                section_name=section_name,
            )

            if driver == "seesaw":
                address = self._i2c_address(
                    section.get("address"),
                    f"{section_name}.address",
                )
                if address in seesaw_addresses:
                    raise CarUiRuntimeConfigError(
                        "Seesaw encoder addresses must be unique"
                    )
                seesaw_addresses.add(address)
                devices.append(
                    SeesawEncoderConfig(
                        address=address,
                        reverse_direction=reverse_direction,
                    )
                )
                continue

            if driver == "gpio":
                pin_a = self._physical_pin(
                    section.get("pin_a"),
                    f"{section_name}.pin_a",
                )
                pin_b = self._physical_pin(
                    section.get("pin_b"),
                    f"{section_name}.pin_b",
                )
                button_value = section.get("button")
                button = (
                    None
                    if button_value is None
                    else self._physical_pin(
                        button_value,
                        f"{section_name}.button",
                    )
                )
                pins = (pin_a, pin_b) + (
                    (button,) if button is not None else ()
                )
                if len(pins) != len(set(pins)):
                    raise CarUiRuntimeConfigError(
                        f"{section_name} pins must be unique"
                    )
                if gpio_pins.intersection(pins):
                    raise CarUiRuntimeConfigError(
                        "GPIO encoder pins cannot be shared"
                    )
                gpio_pins.update(pins)
                devices.append(
                    GpioEncoderConfig(
                        pin_a=pin_a,
                        pin_b=pin_b,
                        button=button,
                        reverse_direction=reverse_direction,
                    )
                )
                continue

            raise CarUiRuntimeConfigError(
                f"{section_name}.driver must be 'seesaw' or 'gpio'"
            )

        return tuple(devices)

    @staticmethod
    def _default_encoder_devices() -> tuple[EncoderDeviceConfig, ...]:
        return (
            SeesawEncoderConfig(address=0x36),
            SeesawEncoderConfig(address=0x37),
            SeesawEncoderConfig(address=0x38),
        )

    def _parse_radios(self, data: Any) -> tuple[RadioStackConfig, ...]:
        if not isinstance(data, list):
            raise CarUiRuntimeConfigError(
                "radios must be an array of tables using [[radios]]"
            )

        radios: list[RadioStackConfig] = []
        seen_keys: set[str] = set()

        for index, item in enumerate(data):
            section_name = f"radios[{index}]"
            section = self._expect_table(item, section_name)

            key = self._required_string(section, "key", section_name)
            config_name = self._required_string(
                section,
                "config",
                section_name,
            )
            backend = self._required_string(
                section,
                "backend",
                section_name,
            )
            launcher = self._optional_nullable_string(
                section,
                "launcher",
                default=None,
                section_name=section_name,
            )
            enabled = self._optional_bool(
                section,
                "enabled",
                default=True,
                section_name=section_name,
            )

            if key in seen_keys:
                raise CarUiRuntimeConfigError(
                    f"Duplicate radio stack key: {key}"
                )
            seen_keys.add(key)

            config_path = self._resolve_radio_config_path(config_name)
            if self.require_radio_files and not config_path.is_file():
                raise CarUiRuntimeConfigError(
                    f"Radio config for '{key}' does not exist: {config_path}"
                )

            radios.append(
                RadioStackConfig(
                    key=key,
                    config_path=config_path,
                    backend=backend,
                    launcher=launcher,
                    enabled=enabled,
                )
            )

        if not radios:
            raise CarUiRuntimeConfigError(
                "At least one [[radios]] entry is required"
            )

        return tuple(radios)

    def _parse_auxiliary(self, data: Any) -> AuxiliaryConfig:
        section = self._expect_table(data, "auxiliary")

        adsb_data = self._expect_table(section.get("adsb", {}), "auxiliary.adsb")
        weather_data = self._expect_table(
            section.get("weather_dashboard", {}),
            "auxiliary.weather_dashboard",
        )

        adsb = AdsbConfig(
            enabled=self._optional_bool(
                adsb_data,
                "enabled",
                default=True,
                section_name="auxiliary.adsb",
            ),
            url=self._optional_string(
                adsb_data,
                "url",
                default="http://127.0.0.1/tar1090",
                section_name="auxiliary.adsb",
            ),
            close_existing_display_apps=self._optional_bool(
                adsb_data,
                "close_existing_display_apps",
                default=True,
                section_name="auxiliary.adsb",
            ),
        )

        weather_dashboard = WeatherDashboardConfig(
            enabled=self._optional_bool(
                weather_data,
                "enabled",
                default=True,
                section_name="auxiliary.weather_dashboard",
            )
        )

        return AuxiliaryConfig(
            adsb=adsb,
            weather_dashboard=weather_dashboard,
        )

    def _resolve_radio_config_path(self, config_name: str) -> Path:
        path = Path(config_name).expanduser()

        if path.is_absolute():
            return path.resolve()

        return (self.radio_config_dir / path).resolve()

    @staticmethod
    def _expect_table(data: Any, section_name: str) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise CarUiRuntimeConfigError(
                f"{section_name} must be a TOML table"
            )
        return data

    @staticmethod
    def _required_string(
        section: dict[str, Any],
        key: str,
        section_name: str,
    ) -> str:
        value = section.get(key)
        if not isinstance(value, str) or not value.strip():
            raise CarUiRuntimeConfigError(
                f"{section_name}.{key} must be a non-empty string"
            )
        return value.strip()

    @classmethod
    def _optional_string(
        cls,
        section: dict[str, Any],
        key: str,
        *,
        default: str,
        section_name: str,
    ) -> str:
        if key not in section:
            return default
        return cls._required_string(section, key, section_name)

    @staticmethod
    def _optional_nullable_string(
        section: dict[str, Any],
        key: str,
        *,
        default: str | None,
        section_name: str,
    ) -> str | None:
        if key not in section:
            return default

        value = section[key]
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise CarUiRuntimeConfigError(
                f"{section_name}.{key} must be a non-empty string"
            )
        return value.strip()

    @staticmethod
    def _optional_bool(
        section: dict[str, Any],
        key: str,
        *,
        default: bool,
        section_name: str,
    ) -> bool:
        value = section.get(key, default)
        if not isinstance(value, bool):
            raise CarUiRuntimeConfigError(
                f"{section_name}.{key} must be a boolean"
            )
        return value

    @staticmethod
    def _i2c_address(value: Any, field_name: str) -> int:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 0 <= value <= 0x7F
        ):
            raise CarUiRuntimeConfigError(
                f"{field_name} must be an integer between 0x00 and 0x7F"
            )
        return value

    @staticmethod
    def _physical_pin(value: Any, field_name: str) -> int:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
        ):
            raise CarUiRuntimeConfigError(
                f"{field_name} must be a positive physical pin number"
            )
        return value

    @staticmethod
    def _default_project_root() -> Path:
        # apps/carUi/config/car_ui_runtime_config_parser.py
        return Path(__file__).resolve().parents[3]
