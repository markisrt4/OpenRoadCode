# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Platform integration metadata loaded from OpenRoadCode catalog data."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_INTEGRATION_DIR = Path(__file__).with_name("catalog") / "integrations"


@dataclass(frozen=True, slots=True)
class BusinessProvider:
    """Execution metadata kept separate from the platform-neutral POI model."""

    provider_id: str
    order_url: str | None = None
    android_package: str | None = None


def _load_integrations(directory: Path = _INTEGRATION_DIR) -> dict[str, BusinessProvider]:
    merged: dict[str, dict[str, str]] = {}

    for path in sorted(directory.glob("*.toml")):
        with path.open("rb") as stream:
            document = tomllib.load(stream)

        for provider_id, raw in document.get("integration", {}).items():
            target = merged.setdefault(provider_id, {})
            for key, value in raw.items():
                if key in target and target[key] != value:
                    raise ValueError(
                        f"Conflicting integration value for {provider_id!r}.{key} in {path}"
                    )
                target[key] = str(value)

    return {
        provider_id: BusinessProvider(
            provider_id=provider_id,
            order_url=values.get("order"),
            android_package=values.get("package"),
        )
        for provider_id, values in merged.items()
    }


_PROVIDERS = _load_integrations()


def get_business_provider(provider_id: str | None) -> BusinessProvider | None:
    """Return execution metadata for a canonical provider identifier."""
    if not provider_id:
        return None
    return _PROVIDERS.get(provider_id)
