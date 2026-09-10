# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Platform launch metadata for canonical POI business providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BusinessProvider:
    """Execution metadata kept separate from the platform-neutral POI model."""

    provider_id: str
    order_url: str | None = None
    android_package: str | None = None


_PROVIDERS = {
    "panera": BusinessProvider(
        provider_id="panera",
        order_url="https://www.panerabread.com/en-us/start-an-order.html",
        android_package="com.panera.bread",
    ),
    "mcdonalds": BusinessProvider(
        provider_id="mcdonalds",
        order_url="https://www.mcdonalds.com/us/en-us.html",
        android_package="com.mcdonalds.app",
    ),
}


def get_business_provider(provider_id: str | None) -> BusinessProvider | None:
    """Return execution metadata for a canonical provider identifier."""
    if not provider_id:
        return None
    return _PROVIDERS.get(provider_id)
