# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Shared vehicle-configuration state for the integrated ORC UI."""

from __future__ import annotations

from collections.abc import Callable

from controllers.automotive import VehicleConfiguration


class VehicleConfigurationState:
    """Own the current vehicle configuration and publish changes."""

    def __init__(
        self,
        configuration: VehicleConfiguration,
        *,
        save: Callable[[VehicleConfiguration], None] | None = None,
    ) -> None:
        self._configuration = configuration
        self._save = save
        self._observers: list[Callable[[VehicleConfiguration], None]] = []

    @property
    def configuration(self) -> VehicleConfiguration:
        return self._configuration

    def observe(
        self,
        observer: Callable[[VehicleConfiguration], None],
    ) -> None:
        self._observers.append(observer)

    def update(self, configuration: VehicleConfiguration) -> None:
        if configuration == self._configuration:
            return
        self._configuration = configuration
        if self._save is not None:
            self._save(configuration)
        for observer in tuple(self._observers):
            observer(configuration)
