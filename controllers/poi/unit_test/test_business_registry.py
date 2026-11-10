# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from dataclasses import replace
import json

import pytest

from controllers.poi.business_catalog import BUSINESSES, resolve_business
from controllers.poi.business_icons import icon_properties
from controllers.poi.poi_enricher import enrich_poi
from scripts.generate_business_registry import CATALOG, generate, serialized, refresh
from ui.navigation import GeoPoint
from ui.navigation.poi_models import PointOfInterest, PoiActionKind, PoiCategory


def test_committed_registry_is_reproducible_offline_from_pinned_snapshot():
    snapshot = json.loads((CATALOG / 'nsi_snapshot.json').read_text())
    overrides = json.loads((CATALOG / 'overrides.json').read_text())
    assert serialized(generate(snapshot, overrides)) == (CATALOG / 'brands.json').read_text()


def test_unknown_schema_or_unpinned_source_is_rejected():
    snapshot = json.loads((CATALOG / 'nsi_snapshot.json').read_text())
    overrides = json.loads((CATALOG / 'overrides.json').read_text())
    with pytest.raises(ValueError, match='schema'):
        generate(dict(snapshot, schema_version=2), overrides)
    with pytest.raises(ValueError, match='commit SHA'):
        generate(dict(snapshot, revision='main'), overrides)


def test_refresh_stops_on_upstream_identity_change_without_mutating_snapshot(monkeypatch):
    from io import BytesIO
    snapshot = json.loads((CATALOG / 'nsi_snapshot.json').read_text())
    original = serialized(snapshot)
    monkeypatch.setattr('scripts.generate_business_registry.urlopen',
                        lambda *args, **kwargs: BytesIO(b'{"items":[]}'))
    with pytest.raises(ValueError, match='identity changed'):
        refresh(snapshot, 'a' * 40)
    assert serialized(snapshot) == original


def test_verified_domain_resolves_a_store_with_an_unhelpful_name():
    assert resolve_business(name='Village Square', website='https://www.panerabread.com/store/123').provider_id == 'panera'
    assert resolve_business(website='https://panerabread.com.evil.example') is None
    assert resolve_business(website='https://panerabread.com@evil.example') is None


def test_conflicting_known_identifiers_or_aliases_remain_unresolved():
    assert resolve_business(brand_wikidata='Q7130852;Q38076') is None
    panera = resolve_business(name='Panera')
    conflicting = replace(panera, provider_id='other-panera')
    assert resolve_business(name='Panera', businesses=(panera, conflicting)) is None


def test_category_collision_never_assigns_a_restaurant_app_to_another_kind_of_poi():
    poi = PointOfInterest('grocery', 'Panera', PoiCategory.GROCERY, GeoPoint(0, 0))
    enriched = enrich_poi(poi)
    assert enriched.business_id is None
    assert enriched.icon_id is None
    assert enriched.actions == ()


def test_branded_search_results_have_one_shared_identity_for_logo_and_actions():
    poi = PointOfInterest('store', 'Unhelpful display name', PoiCategory.FOOD, GeoPoint(0, 0), brand_wikidata='Q38076')
    enriched = enrich_poi(poi)
    assert enriched.business_id == enriched.icon_id == 'mcdonalds'
    assert [(action.kind, action.provider_id) for action in enriched.actions] == [(PoiActionKind.ORDER, enriched.business_id)]
    assert enrich_poi(enriched) == enriched


def test_ordering_is_one_intent_even_when_the_poi_also_has_a_website():
    poi = enrich_poi(PointOfInterest('panera', 'Panera Bread', PoiCategory.FOOD,
                                    GeoPoint(0, 0), website='https://www.panerabread.com'))
    assert [action.kind for action in poi.actions] == [PoiActionKind.ORDER]
    assert poi.website == 'https://www.panerabread.com'


def test_independent_business_still_has_its_website_action():
    poi = enrich_poi(PointOfInterest('cafe', 'Independent Cafe', PoiCategory.FOOD,
                                    GeoPoint(0, 0), website='https://example.com'))
    assert [action.kind for action in poi.actions] == [PoiActionKind.OPEN_WEBSITE]


def test_icon_only_brands_do_not_get_guessed_android_packages():
    poi = PointOfInterest('coffee', 'Starbucks', PoiCategory.FOOD, GeoPoint(0, 0))
    enriched = enrich_poi(poi)
    assert enriched.business_id == enriched.icon_id == 'starbucks'
    assert not any(action.kind is PoiActionKind.OPEN_ANDROID_APP for action in enriched.actions)


def test_missing_or_invalid_icon_keeps_category_fallback_without_reading_arbitrary_files():
    assert icon_properties('unknown-brand') == {}
    assert icon_properties('../../etc/passwd') == {}
    assert icon_properties(None) == {}
    assert icon_properties('mcdonalds')['brand_icon'] == 'business:mcdonalds'


def test_all_generated_icon_references_are_approved_checksummed_assets():
    for business in BUSINESSES:
        if business.icon_id:
            assert icon_properties(business.icon_id)


def test_title_branding_survives_legacy_overrides_and_unknown_brands_use_theme():
    branded = enrich_poi(PointOfInterest('store', "McDonald's", PoiCategory.FOOD, GeoPoint(0, 0)))
    assert branded.title_style.color == '#FBC817'
    assert branded.title_style.font_families[0] == 'Speedee'
    assert enrich_poi(branded) == branded
    unknown = enrich_poi(PointOfInterest('cafe', 'Independent Cafe', PoiCategory.FOOD, GeoPoint(0, 0)))
    assert unknown.title_style is None


@pytest.mark.parametrize('metadata', [
    {'name': 'Burger King'},
    {'name': 'Local restaurant', 'brand_wikidata': 'Q177054'},
    {'name': 'Local restaurant', 'website': 'https://www.bk.com/menu'},
])
def test_burger_king_has_one_order_intent_and_keeps_its_logo(metadata):
    poi = enrich_poi(PointOfInterest('bk', category=PoiCategory.FOOD,
                                    position=GeoPoint(0, 0), **metadata))
    assert poi.business_id == poi.icon_id == 'burger-king'
    assert [(a.kind, a.provider_id) for a in poi.actions] == [(PoiActionKind.ORDER, 'burger-king')]
    assert poi.icon is not None
    assert enrich_poi(poi) == poi


def test_panera_supplies_the_same_bundled_logo_to_map_and_card():
    import base64
    from controllers.poi.business_icons import icon_bytes
    poi = enrich_poi(PointOfInterest('panera', 'Panera Bread', PoiCategory.FOOD, GeoPoint(0, 0)))
    marker = icon_properties('panera')
    assert poi.business_id == poi.icon_id == 'panera'
    assert marker['brand_icon'] == 'business:panera'
    assert poi.icon.data == icon_bytes('panera') == base64.b64decode(marker['brand_icon_png'])
    assert [a.kind for a in poi.actions] == [PoiActionKind.ORDER]


@pytest.mark.parametrize('name,provider', [
    ('Panera Bread', 'panera'),
    ("McDonald's", 'mcdonalds'),
    ('Burger King', 'burger-king'),
])
def test_exact_ordering_brand_survives_an_uncategorized_map_selection(name, provider):
    poi = enrich_poi(PointOfInterest('map-place', name, PoiCategory.OTHER, GeoPoint(0, 0)))
    assert poi.business_id == provider
    assert [(a.kind, a.provider_id) for a in poi.actions] == [(PoiActionKind.ORDER, provider)]


def test_unknown_uncategorized_place_does_not_gain_an_order_action():
    poi = enrich_poi(PointOfInterest('map-place', 'Independent store', PoiCategory.OTHER, GeoPoint(0, 0)))
    assert poi.business_id is None
    assert poi.actions == ()
