# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent, user-owned streaming radio favorites."""

from __future__ import annotations

import json
import os
import tempfile
import tomllib
from pathlib import Path

from controllers.radio.streaming_radio_types import StreamingRadioStation


class StreamingRadioFavorites:
    """Store complete station records so favorites survive directory changes."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "openroadcode" / "streaming_radio.toml"
        self._stations: dict[str, StreamingRadioStation] = {}
        self.load()

    @property
    def stations(self) -> tuple[StreamingRadioStation, ...]:
        return tuple(self._stations.values())

    @property
    def station_ids(self) -> frozenset[str]:
        return frozenset(self._stations)

    def load(self) -> None:
        try:
            data = tomllib.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self._stations = {}
            return
        records = data.get("favorites", [])
        if not isinstance(records, list):
            raise ValueError("favorites must be an array of tables")
        stations = {}
        for record in records:
            station = StreamingRadioStation(**record)
            stations[station.station_id] = station
        self._stations = stations

    def toggle(self, station: StreamingRadioStation) -> bool:
        updated = dict(self._stations)
        if station.station_id in updated:
            del updated[station.station_id]
            favorite = False
        else:
            updated[station.station_id] = station
            favorite = True
        self._save(updated)
        self._stations = updated
        return favorite

    def _save(self, stations: dict[str, StreamingRadioStation]) -> None:
        from dataclasses import fields
        lines = ["# OpenRoadCode streaming radio favorites", "version = 1", ""]
        for station in stations.values():
            lines.append("[[favorites]]")
            for field in fields(station):
                value = getattr(station, field.name)
                if value is None:
                    continue
                if isinstance(value, tuple):
                    value = list(value)
                lines.append(f"{field.name} = {json.dumps(value, ensure_ascii=False)}")
            lines.append("")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, prefix=".streaming_radio-", suffix=".tmp", delete=False) as stream:
                name = stream.name
                stream.write("\n".join(lines))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if name is not None and os.path.exists(name):
                os.unlink(name)
