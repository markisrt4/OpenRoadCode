"""Position-source selection for the Car UI runtime."""

from __future__ import annotations

import os
from pathlib import Path

from controllers.cache import PersistentCache
from controllers.navigation import (
    BrowserPositionSource,
    GpsdPositionSource,
    PersistentPositionSource,
    PositionSnapshotCache,
    PositionSourceIf,
)
from controllers.navigation.position_snapshot_cache import (
    DEFAULT_POSITION_CACHE_DIRECTORY,
)
from config.runtime_config import PositionCacheConfig



def create_position_source(
    provider: str | None = None,
    *,
    cache_config: PositionCacheConfig = PositionCacheConfig(),
) -> PositionSourceIf:
    """Create the configured position provider.

    gpsd remains the default. Additional providers can be added here without
    changing screen, presenter, or application-composition code.
    """
    selected = (
        provider or os.getenv("CARUI_POSITION_SOURCE", "gpsd")
    ).strip().lower()
    if selected == "gpsd":
        source: PositionSourceIf = GpsdPositionSource()
    elif selected == "browser":
        host = os.getenv("CARUI_BROWSER_POSITION_HOST", "127.0.0.1")
        port_text = os.getenv("CARUI_BROWSER_POSITION_PORT", "8765")
        try:
            port = int(port_text)
        except ValueError as exc:
            raise ValueError(
                "CARUI_BROWSER_POSITION_PORT must be an integer"
            ) from exc
        if not 0 <= port <= 65535:
            raise ValueError(
                "CARUI_BROWSER_POSITION_PORT must be between 0 and 65535"
            )
        source = BrowserPositionSource(host=host, port=port)
    else:
        raise ValueError(f"Unsupported position source: {selected}")

    cache_enabled = os.getenv(
        "CARUI_POSITION_CACHE",
        "1" if cache_config.enabled else "0",
    )
    if cache_enabled.strip().lower() in {
        "0", "false", "no", "off"
    }:
        return source
    cache_directory = Path(
        os.getenv(
            "CARUI_POSITION_CACHE_DIRECTORY",
            str(cache_config.directory or DEFAULT_POSITION_CACHE_DIRECTORY),
        )
    ).expanduser()
    try:
        max_age_seconds = float(
            os.getenv(
                "CARUI_POSITION_CACHE_MAX_AGE_SECONDS",
                str(cache_config.max_age_seconds),
            )
        )
    except ValueError as error:
        raise ValueError(
            "CARUI_POSITION_CACHE_MAX_AGE_SECONDS must be numeric"
        ) from error
    return PersistentPositionSource(
        source,
        PositionSnapshotCache(PersistentCache(cache_directory)),
        max_age_seconds=max_age_seconds,
    )
