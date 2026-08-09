"""Position-source selection for the Car UI runtime."""

from __future__ import annotations

import os

from controllers.navigation import (
    BrowserPositionSource,
    GpsdPositionSource,
    PositionSourceIf,
)


def create_position_source(provider: str | None = None) -> PositionSourceIf:
    """Create the configured position provider.

    gpsd remains the default. Additional providers can be added here without
    changing screen, presenter, or application-composition code.
    """
    selected = (
        provider or os.getenv("CARUI_POSITION_SOURCE", "gpsd")
    ).strip().lower()
    if selected == "gpsd":
        return GpsdPositionSource()
    if selected == "browser":
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
        return BrowserPositionSource(host=host, port=port)
    raise ValueError(f"Unsupported position source: {selected}")
