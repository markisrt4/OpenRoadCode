# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from controllers.poi.android_poi_action_executor import AndroidPoiActionExecutor
from ui.navigation.poi_models import (PoiAction, PoiActionKind, PoiCategory, PointOfInterest)
from ui.navigation import GeoPoint


def _panera() -> PointOfInterest:
    return PointOfInterest(
        poi_id="panera",
        name="Panera Bread",
        category=PoiCategory.FOOD,
        position=GeoPoint(0.0, 0.0),
    )


def test_order_resolves_provider_and_prefers_android_app() -> None:
    launcher = Mock()
    launcher.open_package_or_uri.return_value = "app"
    executor = AndroidPoiActionExecutor(launcher)

    status = executor.execute(
        _panera(),
        PoiAction(PoiActionKind.ORDER, "ORDER", provider_id="panera"),
    )

    launcher.open_package_or_uri.assert_called_once_with(
        "com.panera.bread",
        "https://www.panerabread.com/en-us/start-an-order.html",
    )
    assert status == "Opening order in app"


def test_order_reports_web_fallback_from_launcher() -> None:
    launcher = Mock()
    launcher.open_package_or_uri.return_value = "uri"
    executor = AndroidPoiActionExecutor(launcher)

    status = executor.execute(
        _panera(),
        PoiAction(PoiActionKind.ORDER, "ORDER", provider_id="panera"),
    )

    assert status == "Opening order in uri"


def test_android_app_action_uses_only_the_verified_mapping():
    launcher = Mock()
    launcher.open_android_app.return_value = 'Google Play'
    executor = AndroidPoiActionExecutor(launcher)
    status = executor.execute(_panera(), PoiAction(PoiActionKind.OPEN_ANDROID_APP, 'OPEN / INSTALL APP', provider_id='panera'))
    launcher.open_android_app.assert_called_once_with('com.panera.bread')
    assert status == 'Opening Google Play'


def test_app_status_uses_curated_ordering_package_without_launching():
    from dataclasses import replace
    from ui.navigation.poi_models import PoiAppAvailability
    launcher = Mock()
    executor = AndroidPoiActionExecutor(launcher)
    poi = replace(_panera(), actions=(PoiAction(PoiActionKind.ORDER, 'ORDER', provider_id='panera'),))
    for value, expected in ((True, PoiAppAvailability.INSTALLED), (False, PoiAppAvailability.NOT_INSTALLED),
                            (None, PoiAppAvailability.UNKNOWN)):
        launcher.package_installed.return_value = value
        assert executor.app_availability(poi) is expected
    assert executor.app_availability(_panera()) is PoiAppAvailability.WEB_ONLY
    launcher.open_package_or_uri.assert_not_called()


def test_burger_king_order_uses_official_us_package_and_web_fallback():
    from controllers.poi.poi_enricher import enrich_poi
    launcher = Mock()
    launcher.open_package_or_uri.return_value = 'app'
    poi = enrich_poi(PointOfInterest('bk', 'Burger King', PoiCategory.FOOD, GeoPoint(0, 0)))
    action, = poi.actions
    assert AndroidPoiActionExecutor(launcher).execute(poi, action) == 'Opening order in app'
    launcher.open_package_or_uri.assert_called_once_with(
        'com.emn8.mobilem8.nativeapp.bk', 'https://www.bk.com/menu')
