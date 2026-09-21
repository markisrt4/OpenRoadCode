# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from controllers.poi.android_poi_action_executor import AndroidPoiActionExecutor
from controllers.poi.poi_models import PoiAction, PoiActionKind, PoiCategory, PointOfInterest
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
