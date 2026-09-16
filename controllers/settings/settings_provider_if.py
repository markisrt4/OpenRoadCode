# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract for application-wide user settings."""

from __future__ import annotations

from abc import ABC, abstractmethod

from controllers.settings.settings_state import SettingsState


class SettingsProviderIf(ABC):
    """Load and persist application-wide settings."""

    @abstractmethod
    def load(self) -> SettingsState:
        """Return the current settings state."""

    @abstractmethod
    def save(self, state: SettingsState) -> None:
        """Persist the complete settings state."""
