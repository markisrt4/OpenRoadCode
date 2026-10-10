# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Offline address setup orchestration, independent of terminal presentation."""

import sqlite3
from config.saved_destinations import SavedDestinationsConfig, normalize_destination
from ui.navigation.destination_setup_request_handler_if import (
    DestinationSetupRequestHandlerIf, SavedDestination,
)


class DestinationSetupController(DestinationSetupRequestHandlerIf):
    def __init__(self, config: SavedDestinationsConfig, geocoder=None) -> None:
        self._config = config
        self._geocoder = geocoder

    def current(self, key: str) -> SavedDestination | None:
        self._validate_key(key)
        return next((item for item in self._config.load() if item.key == key), None)

    def search(self, key: str, address: str) -> tuple[SavedDestination, ...]:
        self._validate_key(key)
        address = " ".join(address.split())
        if not address:
            raise ValueError("Enter an address")
        if self._geocoder is None:
            return ()
        try:
            results = self._geocoder.geocode(address)
        except sqlite3.Error as error:
            raise RuntimeError("Local address database unavailable; enter coordinates instead") from error
        return tuple(normalize_destination(SavedDestination(
            key, key.title(), result.display_name, result.position,
        )) for result in results)

    def save(self, destination: SavedDestination) -> None:
        self._config.save(destination)

    @staticmethod
    def _validate_key(key: str) -> None:
        if key not in {"home", "work"}:
            raise ValueError("Destination must be home or work")
