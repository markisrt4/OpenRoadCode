# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Receive POI selections published by the native map renderer."""
from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, SimpleQueue
from threading import Thread
from typing import Any

from messaging.zeromq.subscriber import ZeroMqSubscriber

POI_SELECTED_TOPIC = "map.poi.selected"


@dataclass(frozen=True)
class MapPoiSelection:
    name: str
    brand: str
    latitude: float
    longitude: float


class MapPoiSelectionSource:
    def __init__(self) -> None:
        self._subscriber = ZeroMqSubscriber()
        self._subscriber.subscribe(POI_SELECTED_TOPIC)
        self._queue: SimpleQueue[MapPoiSelection] = SimpleQueue()
        self._thread = Thread(target=self._receive, name="map-poi-selection", daemon=True)
        self._thread.start()

    def poll(self) -> MapPoiSelection | None:
        try:
            return self._queue.get_nowait()
        except Empty:
            return None

    def close(self) -> None:
        self._subscriber.close()

    def _receive(self) -> None:
        while True:
            try:
                topic, payload = self._subscriber.receive()
            except RuntimeError:
                return
            if topic != POI_SELECTED_TOPIC:
                continue
            selection = self._decode(payload)
            if selection is not None:
                self._queue.put(selection)

    @staticmethod
    def _decode(payload: dict[str, Any] | Any) -> MapPoiSelection | None:
        if not isinstance(payload, dict):
            return None
        name = payload.get("name")
        brand = payload.get("brand", "")
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        if not isinstance(name, str) or not name:
            return None
        if not isinstance(brand, str):
            brand = ""
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return None
        return MapPoiSelection(name, brand, float(latitude), float(longitude))
