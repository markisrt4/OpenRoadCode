# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Platform-independent contract for executing semantic POI actions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.poi.poi_models import PoiAction, PointOfInterest


class PoiActionExecutorIf(ABC):
    """Execute a semantic POI action using the active platform."""

    @abstractmethod
    def execute(self, poi: PointOfInterest, action: PoiAction) -> str:
        """Execute an action and return a short user-facing status description."""
