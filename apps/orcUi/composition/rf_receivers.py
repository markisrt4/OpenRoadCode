# SPDX-License-Identifier: MIT
"""Compose managed SDRForge receiver lifecycles and service endpoints."""

from __future__ import annotations

import re

from common.resource_cleanup import close_resources
from controllers.radio.managed_receivers import ManagedReceivers
from controllers.radio.receiver_acquisition import ReceiverAcquisitionController
from controllers.radio.receiver_assignments import ReceiverAssignmentStore
from controllers.radio.receiver_ownership import ReceiverOwnershipController
from hardware_io.rf.readsb_acquisition_adapter import ReadsbAcquisitionAdapter
from hardware_io.rf.readsb_systemd_service import ReadsbSystemdService
from hardware_io.rf.receiver_discovery_if import ReceiverDiscoveryIf
from hardware_io.rf.sdrforge_acquisition_adapter import SdrforgeAcquisitionAdapter
from services.linux.sdrforge_instance import SdrForgeSystemdInstance

RADIO_REST = "http://127.0.0.1:5570"
WEATHER_REST = "http://127.0.0.1:5572"


class ManagedReceiverServices:
    """Share the primary instance for one receiver and use a secondary one for NOAA."""

    def __init__(
        self,
        token: str,
        ownership: ReceiverOwnershipController,
        assignments: ReceiverAssignmentStore,
        discovery: ReceiverDiscoveryIf,
    ) -> None:
        self._ownership = ownership
        self._assignments = assignments
        self._consumers = ManagedReceivers(
            ReceiverAcquisitionController(ownership), assignments, discovery
        )
        self._radio = self._adapter(token, "libsdrforge.service", RADIO_REST)
        self._weather = self._adapter(token, "libsdrforge-weather.service", WEATHER_REST)
        self._adsb_service: ReadsbSystemdService | None = None

    @staticmethod
    def _adapter(token: str, unit: str, endpoint: str) -> SdrforgeAcquisitionAdapter:
        instance = SdrForgeSystemdInstance(unit, endpoint)
        return SdrforgeAcquisitionAdapter(token, endpoint, ensure_ready=instance.ensure_ready)

    def start_radio(self) -> None:
        device = self._consumers.assignment("radio")
        for lease in self._ownership.snapshot():
            if lease.identity == device.identity and lease.consumer == "weather":
                self._consumers.stop("weather")
        self._consumers.start("radio", device, self._radio)

    def stop_radio(self) -> None:
        self._consumers.stop("radio")

    def start_weather(self) -> str:
        device = self._consumers.assignment("weather")
        shared = self._assignments.load().radio == device.identity
        adapter = self._radio if shared else self._weather
        self._consumers.start("weather", device, adapter)
        return RADIO_REST if shared else WEATHER_REST

    def adsb_active(self) -> bool:
        return self._adsb_service is not None and self._adsb_service.active()

    def set_adsb_tracking(self, enabled: bool) -> bool:
        if not enabled:
            self._consumers.stop("adsb")
            self._adsb_service = None
            return False
        if self.adsb_active():
            return True
        self._consumers.stop("adsb")
        device = self._consumers.assignment("adsb")
        serial = device.serial
        # readsb interprets ordinary integers as indices before matching serials.
        if not re.fullmatch(r"[A-Za-z0-9_]+", serial) or (
            serial.isdecimal() and (len(serial) == 1 or not serial.startswith("0"))
        ):
            raise RuntimeError(
                "ADS-B requires an alphanumeric USB serial or a numeric serial with leading zeroes"
            )
        service = ReadsbSystemdService(
            serial, unit=f"openroadcode-readsb@{serial}.service", user_unit=True
        )
        self._adsb_service = service
        self._consumers.start("adsb", device, ReadsbAcquisitionAdapter(service))
        return True

    def close(self) -> None:
        close_resources(
            self.stop_radio,
            lambda: self._consumers.stop("weather"),
            lambda: self.set_adsb_tracking(False),
        )
