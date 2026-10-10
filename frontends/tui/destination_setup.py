# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Installer destination presentation using only UI contracts."""

import math

from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.destination_setup_request_handler_if import (
    DestinationSetupRequestHandlerIf, SavedDestination,
)
from ui.navigation.destination_setup_ui_if import DestinationSetupUiIf


def run_destination_setup(handler: DestinationSetupRequestHandlerIf,
                          dialog: DestinationSetupUiIf) -> None:
    """Edit individual destinations; abandoned drafts never reach storage."""
    while True:
        key = dialog.choose("Home and Work", "Choose an address to configure:", (
            ("home", "Home address"), ("work", "Work address"), ("done", "Finish"),
        ))
        if key is None or key == "done":
            return
        try:
            _edit_destination(handler, dialog, key)
        except (OSError, ValueError, RuntimeError) as error:
            dialog.notify("Destination not saved", str(error))


def _edit_destination(handler, dialog, key) -> None:
    current = handler.current(key)
    address = dialog.text(key.title(), "Enter the full address:",
                          current.address if current else "")
    if address is None:
        return
    if not address.strip():
        raise ValueError("Enter an address")
    try:
        candidates = handler.search(key, address)
    except (OSError, ValueError, RuntimeError) as error:
        dialog.notify("Address search unavailable", str(error))
        candidates = ()
    choices = tuple((str(i), f"{item.address} ({math.degrees(item.position.latitude_rad):.5f}, "
                     f"{math.degrees(item.position.longitude_rad):.5f})")
                    for i, item in enumerate(candidates))
    selection = dialog.choose(key.title(), "Select the correct match, or enter coordinates:",
                               choices + (("manual", "Enter coordinates in degrees"),))
    if selection is None:
        return
    if selection == "manual":
        latitude = dialog.text(key.title(), "Latitude in degrees (-90 to 90):")
        if latitude is None:
            return
        longitude = dialog.text(key.title(), "Longitude in degrees (-180 to 180):")
        if longitude is None:
            return
        destination = SavedDestination(key, key.title(), address,
            GeoPoint(math.radians(float(latitude)), math.radians(float(longitude))))
    else:
        destination = candidates[int(selection)]
    position = destination.position
    if (not math.isfinite(position.latitude_rad) or not math.isfinite(position.longitude_rad)
            or not -math.pi / 2 <= position.latitude_rad <= math.pi / 2
            or not -math.pi <= position.longitude_rad <= math.pi):
        raise ValueError("Coordinates are out of range")
    summary = (f"{destination.address}\n\n"
               f"Latitude: {math.degrees(position.latitude_rad):.6f}°\n"
               f"Longitude: {math.degrees(position.longitude_rad):.6f}°\n\n"
               "Save this destination? Navigation starts only when you choose Navigate in ORC.")
    if dialog.confirm(key.title(), summary):
        handler.save(destination)
        dialog.notify("Destination saved", f"{key.title()} saved. Reopen Navigation in ORC to reload it.")
