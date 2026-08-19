# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import asyncio
from collections.abc import Callable
from threading import Lock
from typing import Any

from hardware_io.bluetooth.ble_gatt_transport_if import (
    BleGattState,
    BleGattStatus,
    BleGattTransportIf,
)

try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.device import BLEDevice
except ImportError:  # pragma: no cover
    BleakClient = None  # type: ignore[assignment]
    BleakScanner = None  # type: ignore[assignment]
    BLEDevice = None  # type: ignore[assignment,misc]


class BleakUnavailableError(RuntimeError):
    """Raised when the Bleak-backed transport cannot be constructed."""


class BleakGattTransport(BleGattTransportIf):
    """Bleak implementation for one independently owned GATT connection."""

    def __init__(
        self,
        *,
        characteristic_uuid: str,
        address: str | None = None,
        excluded_service_uuids: tuple[str, ...] = (),
        excluded_name_fragments: tuple[str, ...] = (),
        write_with_response: bool = False,
        command_delay_seconds: float = 0.05,
        reconnect_delay_seconds: float = 0.25,
        scan_timeout_seconds: float = 15.0,
        connect_timeout_seconds: float = 8.0,
        state_callback: Callable[[BleGattState], None] | None = None,
    ) -> None:
        if BleakClient is None or BleakScanner is None:
            raise BleakUnavailableError(
                "bleak is not installed. Install with: pip install bleak"
            )

        self._characteristic_uuid = characteristic_uuid.lower()
        self._address = address.strip() if address else None
        self._excluded_service_uuids = {value.lower() for value in excluded_service_uuids}
        self._excluded_name_fragments = tuple(value.lower() for value in excluded_name_fragments)
        self._write_with_response = write_with_response
        self._command_delay_seconds = command_delay_seconds
        self._reconnect_delay_seconds = reconnect_delay_seconds
        self._scan_timeout_seconds = scan_timeout_seconds
        self._connect_timeout_seconds = connect_timeout_seconds
        self._state_callback = state_callback
        self._client: BleakClient | None = None
        self._lock: asyncio.Lock | None = None
        self._state = BleGattState(address=self._address)
        self._state_lock = Lock()
        self._intentional_disconnect = False
        self._resolved_address = self._address

    def current_state(self) -> BleGattState:
        with self._state_lock:
            return self._state

    async def connect(self) -> None:
        await self._ensure_lock()
        assert self._lock is not None
        async with self._lock:
            self._set_state(BleGattStatus.CONNECTING)
            try:
                await self._connect_unlocked()
            except Exception as exc:
                self._set_state(BleGattStatus.ERROR, error=str(exc))
                raise

    async def disconnect(self) -> None:
        await self._ensure_lock()
        assert self._lock is not None
        async with self._lock:
            self._intentional_disconnect = True
            try:
                if self._client is not None and self._client.is_connected:
                    await self._client.disconnect()
            finally:
                self._intentional_disconnect = False
            self._client = None
            self._set_state(BleGattStatus.DISCONNECTED)

    async def write(self, data: bytes) -> None:
        await self._ensure_lock()
        assert self._lock is not None
        async with self._lock:
            await self._connect_unlocked()
            try:
                await self._write_unlocked(data)
            except Exception:
                await self._disconnect_client_unlocked()
                self._set_state(BleGattStatus.RECONNECTING)
                await asyncio.sleep(self._reconnect_delay_seconds)
                try:
                    await self._connect_unlocked()
                    await self._write_unlocked(data)
                except Exception as exc:
                    self._set_state(BleGattStatus.ERROR, error=str(exc))
                    raise
            self._set_state(BleGattStatus.CONNECTED)
            if self._command_delay_seconds > 0:
                await asyncio.sleep(self._command_delay_seconds)

    async def _ensure_lock(self) -> None:
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def _connect_unlocked(self) -> None:
        if self._client is not None and self._client.is_connected:
            self._set_state(BleGattStatus.CONNECTED)
            return
        client = await self._connect_address() if self._address is not None else await self._discover_target()
        self._client = client
        self._set_state(BleGattStatus.CONNECTED)

    async def _connect_address(self) -> BleakClient:
        assert BleakScanner is not None
        device = await BleakScanner.find_device_by_address(self._address, timeout=self._scan_timeout_seconds)
        if device is None:
            raise RuntimeError(f"BLE device {self._address} was not visible during a {self._scan_timeout_seconds:g}-second scan")
        client = self._new_client(device)
        await client.connect()
        if not self._has_target_characteristic(client):
            await client.disconnect()
            raise RuntimeError(f"Device {self._address} does not expose characteristic {self._characteristic_uuid}")
        self._resolved_address = device.address
        return client

    async def _discover_target(self) -> BleakClient:
        assert BleakScanner is not None
        discovered = await BleakScanner.discover(return_adv=True, timeout=self._scan_timeout_seconds)
        candidates = [(device, advertisement) for device, advertisement in discovered.values() if not self._is_excluded(device, advertisement)]
        candidates.sort(key=lambda item: getattr(item[1], "rssi", -999), reverse=True)
        errors: list[str] = []
        for device, advertisement in candidates:
            name = device.name or getattr(advertisement, "local_name", None) or "unnamed"
            client = self._new_client(device)
            try:
                await client.connect()
                if self._has_target_characteristic(client):
                    self._resolved_address = device.address
                    return client
                await client.disconnect()
                errors.append(f"{device.address} ({name}): characteristic absent")
            except Exception as exc:
                try:
                    if client.is_connected:
                        await client.disconnect()
                except Exception:
                    pass
                errors.append(f"{device.address} ({name}): {exc}")
        details = "; ".join(errors[:8]) or "no BLE candidates discovered"
        raise RuntimeError(f"No BLE device exposed characteristic {self._characteristic_uuid}. Tried: {details}")

    def _new_client(self, device: BLEDevice) -> BleakClient:
        assert BleakClient is not None
        return BleakClient(device, timeout=self._connect_timeout_seconds, disconnected_callback=self._on_disconnected)

    def _has_target_characteristic(self, client: BleakClient) -> bool:
        return any(characteristic.uuid.lower() == self._characteristic_uuid for service in client.services for characteristic in service.characteristics)

    def _is_excluded(self, device: BLEDevice, advertisement: Any) -> bool:
        name = (device.name or getattr(advertisement, "local_name", None) or "").lower()
        services = {value.lower() for value in getattr(advertisement, "service_uuids", ())}
        return any(fragment in name for fragment in self._excluded_name_fragments) or bool(services & self._excluded_service_uuids)

    async def _write_unlocked(self, data: bytes) -> None:
        if self._client is None:
            raise RuntimeError("BLE transport is not connected")
        await self._client.write_gatt_char(self._characteristic_uuid, data, response=self._write_with_response)

    async def _disconnect_client_unlocked(self) -> None:
        client = self._client
        self._client = None
        if client is not None and client.is_connected:
            self._intentional_disconnect = True
            try:
                await client.disconnect()
            finally:
                self._intentional_disconnect = False

    def _on_disconnected(self, client: BleakClient) -> None:
        if client is not self._client:
            return
        self._client = None
        if self._intentional_disconnect:
            self._set_state(BleGattStatus.DISCONNECTED)
        else:
            self._set_state(BleGattStatus.RECONNECTING, error="Bluetooth connection was lost")

    def _set_state(self, status: BleGattStatus, *, error: str | None = None) -> None:
        state = BleGattState(status=status, address=self._resolved_address, last_error=error)
        with self._state_lock:
            self._state = state
        if self._state_callback is not None:
            self._state_callback(state)
