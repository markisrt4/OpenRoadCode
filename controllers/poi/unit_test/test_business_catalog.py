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


def test_catalog_loads_capabilities_from_toml() -> None:
    business = resolve_business(name="Panera Bread")
    assert business is not None
    assert business.categories == frozenset({"food"})
    assert business.capabilities == frozenset({"order"})


def test_structured_identity_wins_over_conflicting_display_names():
    business = resolve_business(brand_wikidata='Q7130852', brand="McDonald's", name='Local Cafe')
    assert business.provider_id == 'panera'


def test_operator_alias_can_identify_a_local_store():
    assert resolve_business(operator='Saint Louis Bread Co.', name='Village Square').provider_id == 'panera'


def test_name_matching_does_not_match_business_name_substrings():
    assert resolve_business(name='Cafe next to Panera Bread') is None


def test_unknown_identity_falls_back_to_exact_brand():
    assert resolve_business(brand_wikidata='Q999999999', brand='Panera').provider_id == 'panera'
