# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Platform launch metadata loaded from the OpenRoadCode business catalog."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_CATALOG_PATH = Path(__file__).with_name("businesses.toml")


@dataclass(frozen=True, slots=True)
class BusinessProvider:
    """Execution metadata kept separate from the platform-neutral POI model."""

    provider_id: str
    order_url: str | None = None
    android_package: str | None = None


def _load_providers(path: Path = _CATALOG_PATH) -> dict[str, BusinessProvider]:
    with path.open("rb") as stream:
        document = tomllib.load(stream)

    providers: dict[str, BusinessProvider] = {}
    for provider_id, raw in document.get("business", {}).items():
        web = raw.get("web", {})
        android = raw.get("android", {})
        providers[provider_id] = BusinessProvider(
            provider_id=provider_id,
            order_url=web.get("order"),
            android_package=android.get("package"),
        )
    return providers


_PROVIDERS = _load_providers()


def get_business_provider(provider_id: str | None) -> BusinessProvider | None:
    """Return execution metadata for a canonical provider identifier."""
    if not provider_id:
        return None
    return _PROVIDERS.get(provider_id)
