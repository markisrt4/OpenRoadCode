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
    address = dialog.text(key.title(), "Enter the full US address. Local search runs first; "
                          "online search, when enabled, sends this address to the US Census geocoder:",
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
    if not candidates:
        try:
            candidates = handler.search_online(key, address)
        except (OSError, ValueError, RuntimeError) as error:
            dialog.notify("Online search unavailable", str(error))
    choices = tuple((str(i), item.address)
                    for i, item in enumerate(candidates))
    prompt = ("Select your address, then check its location on the map:" if candidates else
              "No address match. Cancel and try a more complete address, "
              "or use the advanced option below:")
    selection = dialog.choose(key.title(), prompt,
                               choices + (("manual", "Advanced: enter coordinates"),))
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
        destination = dialog.confirm_location(destination)
        if destination is None:
            return
    position = destination.position
    if (not math.isfinite(position.latitude_rad) or not math.isfinite(position.longitude_rad)
            or not -math.pi / 2 <= position.latitude_rad <= math.pi / 2
            or not -math.pi <= position.longitude_rad <= math.pi):
        raise ValueError("Coordinates are out of range")
    summary = (f"{destination.address}\n\n"
               "Save this destination? Navigation starts only when you choose Navigate in ORC.")
    if dialog.confirm(key.title(), summary):
        handler.save(destination)
        dialog.notify("Destination saved", f"{key.title()} saved. Reopen Navigation in ORC to reload it.")
