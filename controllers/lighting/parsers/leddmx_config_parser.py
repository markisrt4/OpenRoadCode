from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LEDDMX_CONFIG_PATH = PROJECT_ROOT / "config" / "lighting"


class LedDmxConfigError(ValueError):
    """Raised when the LEDDMX TOML configuration is invalid."""


@dataclass(frozen=True, slots=True)
class LedDmxBluetoothConfig:
    service_uuid: str
    characteristic_uuid: str
    excluded_service_uuids: tuple[str, ...]
    excluded_name_fragments: tuple[str, ...]
    write_with_response: bool
    command_delay_seconds: float
    reconnect_delay_seconds: float
    scan_timeout_seconds: float
    candidate_connect_timeout_seconds: float


def load_leddmx_config(
    config_path: str | Path | None = None,
    *,
    project_root: str | Path | None = None,
) -> LedDmxBluetoothConfig:
    root = (
        Path(project_root).expanduser().resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    path = (
        Path(config_path).expanduser()
        if config_path is not None
        else DEFAULT_LEDDMX_CONFIG_PATH
    )
    if not path.is_absolute():
        path = root / path
    if path.is_dir():
        path = path / "leddmx.toml"
    path = path.resolve()

    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except FileNotFoundError as exc:
        raise LedDmxConfigError(
            f"LEDDMX config file not found: {path}"
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise LedDmxConfigError(
            f"Invalid TOML in {path}: {exc}"
        ) from exc

    bluetooth = _table(data.get("bluetooth"), "bluetooth")
    discovery = _table(data.get("discovery", {}), "discovery")

    return LedDmxBluetoothConfig(
        service_uuid=_uuid(
            bluetooth,
            "service_uuid",
            "bluetooth",
        ),
        characteristic_uuid=_uuid(
            bluetooth,
            "characteristic_uuid",
            "bluetooth",
        ),
        excluded_service_uuids=tuple(
            _uuid_value(value, "bluetooth.excluded_service_uuids")
            for value in _string_list(
                bluetooth,
                "excluded_service_uuids",
                default=(),
                section_name="bluetooth",
            )
        ),
        excluded_name_fragments=tuple(
            value.lower()
            for value in _string_list(
                discovery,
                "excluded_name_fragments",
                default=(),
                section_name="discovery",
            )
        ),
        write_with_response=_boolean(
            bluetooth,
            "write_with_response",
            default=False,
            section_name="bluetooth",
        ),
        command_delay_seconds=_nonnegative_number(
            bluetooth,
            "command_delay_seconds",
            default=0.05,
            section_name="bluetooth",
        ),
        reconnect_delay_seconds=_nonnegative_number(
            bluetooth,
            "reconnect_delay_seconds",
            default=0.25,
            section_name="bluetooth",
        ),
        scan_timeout_seconds=_positive_number(
            bluetooth,
            "scan_timeout_seconds",
            default=15.0,
            section_name="bluetooth",
        ),
        candidate_connect_timeout_seconds=_positive_number(
            bluetooth,
            "candidate_connect_timeout_seconds",
            default=8.0,
            section_name="bluetooth",
        ),
    )


def _table(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LedDmxConfigError(f"{name} must be a TOML table")
    return value


def _uuid(
    section: dict[str, Any],
    key: str,
    section_name: str,
) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LedDmxConfigError(
            f"{section_name}.{key} must be a UUID string"
        )
    return _uuid_value(value, f"{section_name}.{key}")


def _uuid_value(value: str, field_name: str) -> str:
    try:
        return str(uuid.UUID(value.strip()))
    except (ValueError, AttributeError) as exc:
        raise LedDmxConfigError(
            f"{field_name} contains an invalid UUID: {value!r}"
        ) from exc


def _string_list(
    section: dict[str, Any],
    key: str,
    *,
    default: tuple[str, ...],
    section_name: str,
) -> tuple[str, ...]:
    value = section.get(key, list(default))
    if not isinstance(value, list):
        raise LedDmxConfigError(
            f"{section_name}.{key} must be an array of strings"
        )

    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise LedDmxConfigError(
                f"{section_name}.{key} must contain non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def _boolean(
    section: dict[str, Any],
    key: str,
    *,
    default: bool,
    section_name: str,
) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise LedDmxConfigError(
            f"{section_name}.{key} must be a boolean"
        )
    return value


def _positive_number(
    section: dict[str, Any],
    key: str,
    *,
    default: float,
    section_name: str,
) -> float:
    value = _number(section, key, default, section_name)
    if value <= 0:
        raise LedDmxConfigError(
            f"{section_name}.{key} must be greater than zero"
        )
    return value


def _nonnegative_number(
    section: dict[str, Any],
    key: str,
    *,
    default: float,
    section_name: str,
) -> float:
    value = _number(section, key, default, section_name)
    if value < 0:
        raise LedDmxConfigError(
            f"{section_name}.{key} must not be negative"
        )
    return value


def _number(
    section: dict[str, Any],
    key: str,
    default: float,
    section_name: str,
) -> float:
    value = section.get(key, default)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
    ):
        raise LedDmxConfigError(
            f"{section_name}.{key} must be numeric"
        )
    return float(value)
