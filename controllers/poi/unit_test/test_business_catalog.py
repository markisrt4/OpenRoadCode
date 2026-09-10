# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.poi.business_catalog import resolve_business


def test_panera_alias_resolves_to_canonical_business() -> None:
    business = resolve_business(name="St Louis Bread Co")
    assert business is not None
    assert business.provider_id == "panera"
    assert business.brand == "Panera Bread"
    assert "order" in business.capabilities


def test_explicit_brand_is_preferred_over_name() -> None:
    business = resolve_business(brand="Panera", name="McDonald's")
    assert business is not None
    assert business.provider_id == "panera"
