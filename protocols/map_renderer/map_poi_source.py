# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Adapter for generic POI selections emitted by the native map renderer."""

from __future__ import annotations

import math
from dataclasses import dataclass
from queue import Empty, SimpleQueue
from threading import Thread
from typing import Any

from messaging.zeromq.subscriber import ZeroMqSubscriber
from ui.navigation import GeoPoint

POI_SELECTED_TOPIC = "map.poi.selected"


@dataclass(frozen=True, slots=True)
class RawMapPoi:
    poi_id: str
    name: str
    position: GeoPoint
    brand: str | None = None
    source_class: str | None = None
    source_subclass: str | None = None


class MapPoiSource:
    """Marshal native renderer POI events onto the controller/UI thread."""

    def __init__(self) -> None:
        self._subscriber = ZeroMqSubscriber()
        self._subscriber.subscribe(POI_SELECTED_TOPIC)
        self._queue: SimpleQueue[RawMapPoi] = SimpleQueue()
        self._thread = Thread(target=self._receive, name="map-poi-source", daemon=True)
        self._thread.start()

    def poll_selected(self) -> RawMapPoi | None:
        try:
            return self._queue.get_nowait()
        except Empty:
            return None

    def request_search(self, category: str) -> None:
        """Request POI discovery.

        Search transport is intentionally added separately from selection events;
        this keeps the public POI controller independent of renderer protocol details.
        """
        del category

    def clear(self) -> None:
        """Clear renderer POI search state once search transport is available."""

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
            poi = self._decode(payload)
            if poi is not None:
                self._queue.put(poi)

    @staticmethod
    def _decode(payload: Any) -> RawMapPoi | None:
        if not isinstance(payload, dict):
            return None
        name = payload.get("name")
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        if not isinstance(name, str) or not name:
            return None
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return None

        def optional_string(key: str) -> str | None:
            value = payload.get(key)
            return value if isinstance(value, str) and value else None

        poi_id = optional_string("id") or f"map:{name}:{float(latitude):.7f}:{float(longitude):.7f}"
        return RawMapPoi(
            poi_id=poi_id,
            name=name,
            position=GeoPoint(
                latitude_rad=math.radians(float(latitude)),
                longitude_rad=math.radians(float(longitude)),
            ),
            brand=optional_string("brand"),
            source_class=optional_string("class"),
            source_subclass=optional_string("subclass"),
        )
