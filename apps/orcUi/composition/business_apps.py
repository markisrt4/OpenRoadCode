# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Compose a separate native-phone surface for curated business applications."""
from apps.launchers.scrcpy_business_app_launcher import ScrcpyBusinessAppLauncher
from apps.orcUi.adapters.scrcpy_waze_player import ScrcpyAppPlayer
from apps.orcUi.composition.android_app_view import AndroidAppView
from controllers.poi.business_catalog import BUSINESSES
from controllers.poi.business_provider_catalog import get_business_provider
from frontends.x11.x11_window_embedder import X11WindowEmbedder


def configure_termux_business_apps(app, *, map_runtime, map_platform, map_presentation):
    packages = {}
    for business in BUSINESSES:
        provider = get_business_provider(business.provider_id)
        if provider is not None and provider.android_package:
            packages[provider.android_package] = business.brand
    if not packages:
        return None, None
    player = ScrcpyAppPlayer(package=next(iter(packages)))
    view = AndroidAppView(app, map_runtime=map_runtime, map_platform=map_platform,
        map_presentation=map_presentation, player=player, window_embedder=X11WindowEmbedder(),
        preserve_external_window=False, prepare_app=player.prepare_package, full_width_apps=True)
    return view, ScrcpyBusinessAppLauncher(packages, stop_viewer=player.stop)
