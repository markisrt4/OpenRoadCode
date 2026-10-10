# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""User-owned Home/Work TOML, separate from installed runtime policy."""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from common.xdg_paths import openroadcode_config_dir
from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.destination_setup_request_handler_if import SavedDestination


def normalize_destination(destination: SavedDestination) -> SavedDestination:
    if destination.key not in {"home", "work"}:
        raise ValueError("Destination must be home or work")
    position = destination.position
    lat, lon = position.latitude_rad, position.longitude_rad
    if type(lat) not in (int, float) or type(lon) not in (int, float):
        raise ValueError("Destination coordinates must be numbers")
    try:
        lat, lon = float(lat), float(lon)
    except OverflowError as error:
        raise ValueError("Destination coordinates are out of range") from error
    if (not math.isfinite(lat) or not math.isfinite(lon)
            or not -math.pi / 2 <= lat <= math.pi / 2
            or not -math.pi <= lon <= math.pi):
        raise ValueError("Destination coordinates are out of range")
    label = " ".join(destination.label.split()) or destination.key.title()
    address = " ".join(destination.address.split())
    return SavedDestination(destination.key, label, address, GeoPoint(float(lat), float(lon)))


class SavedDestinationsConfig:
    """Validate before atomic replacement; never overwrite malformed configuration."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else openroadcode_config_dir("destinations.toml")

    def load(self) -> tuple[SavedDestination, ...]:
        try:
            with self.path.open("rb") as source:
                data = tomllib.load(source)
        except FileNotFoundError:
            return ()
        if type(data.get("version")) is not int or data["version"] != 1:
            raise ValueError("Unsupported saved destinations version")
        if set(data) - {"version", "home", "work"}:
            raise ValueError("Unknown saved destinations settings")
        destinations = []
        for key in ("home", "work"):
            if key not in data:
                continue
            record = data[key]
            try:
                if not isinstance(record, dict) or set(record) != {
                    "label", "address", "latitude_rad", "longitude_rad"
                }:
                    raise ValueError("Invalid destination fields")
                if not isinstance(record["label"], str) or not isinstance(record["address"], str):
                    raise ValueError("Destination labels must be text")
                if any(type(record[field]) not in (int, float)
                       for field in ("latitude_rad", "longitude_rad")):
                    raise ValueError("Destination coordinates must be numbers")
                destination = SavedDestination(key, record["label"], record["address"],
                    GeoPoint(record["latitude_rad"], record["longitude_rad"]))
                destinations.append(normalize_destination(destination))
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid {key} destination: {error}") from error
        return tuple(destinations)

    def save(self, destination: SavedDestination) -> None:
        destination = normalize_destination(destination)
        records = {item.key: item for item in self.load()}
        records[destination.key] = destination
        lines = ["# User-owned saved destinations; angular coordinates are radians.", "version = 1", ""]
        for key in ("home", "work"):
            if key not in records:
                continue
            item = records[key]
            label = json.dumps(item.label, ensure_ascii=False).replace("\x7f", "\\u007f")
            address = json.dumps(item.address, ensure_ascii=False).replace("\x7f", "\\u007f")
            lines.extend([f"[{key}]", f"label = {label}",
                          f"address = {address}",
                          f"latitude_rad = {item.position.latitude_rad!r}",
                          f"longitude_rad = {item.position.longitude_rad!r}", ""])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".destinations-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write("\n".join(lines))
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)
