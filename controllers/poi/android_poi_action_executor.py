# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Android implementation of semantic business POI actions."""

from __future__ import annotations

from apps.launchers.android_intent_launcher import AndroidIntentLauncher
from controllers.poi.business_provider_catalog import get_business_provider
from controllers.poi.poi_action_executor_if import PoiActionExecutorIf
from controllers.poi.poi_models import PoiAction, PoiActionKind, PointOfInterest


class AndroidPoiActionExecutor(PoiActionExecutorIf):
    """Translate semantic POI actions into Android app or web launches."""

    def __init__(self, launcher: AndroidIntentLauncher | None = None) -> None:
        self._launcher = launcher or AndroidIntentLauncher()

    def execute(self, poi: PointOfInterest, action: PoiAction) -> str:
        del poi
        if action.kind is PoiActionKind.OPEN_WEBSITE:
            if not action.uri:
                raise ValueError("OPEN_WEBSITE action requires a URI")
            self._launcher.open_uri(action.uri)
            return f"Opening {action.label.casefold()}"

        if action.kind is PoiActionKind.ORDER:
            provider = get_business_provider(action.provider_id)
            if provider is None or not provider.order_url:
                raise ValueError(f"No ordering destination for provider {action.provider_id!r}")
            destination = self._launcher.open_package_or_uri(
                provider.android_package,
                provider.order_url,
            )
            return f"Opening {action.label.casefold()} in {destination}"

        raise ValueError(f"Unsupported external POI action: {action.kind.name}")
