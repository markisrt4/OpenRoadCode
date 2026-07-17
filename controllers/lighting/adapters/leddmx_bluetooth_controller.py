from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any

from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.lighting.lighting_types import (
    CustomPatternMode,
    LightingState,
    RgbColor,
)
from protocols.leddmx.leddmx_protocol import LedDmxProtocol
from controllers.lighting.parsers.leddmx_config_parser import (
    LedDmxBluetoothConfig,
    load_leddmx_config,
)

try:
    from bleak import BleakClient, BleakScanner
    from bleak.backends.device import BLEDevice
except ImportError:  # pragma: no cover - lets the package import without BLE deps installed
    BleakClient = None  # type: ignore[assignment]
    BleakScanner = None  # type: ignore[assignment]
    BLEDevice = None  # type: ignore[assignment,misc]


class BleakUnavailableError(RuntimeError):
    """Raised when Bluetooth lighting is requested without bleak installed."""


class LedDmxBluetoothController(LightingControllerIf):
    """Persistent LEDDMX BLE controller with its own asyncio event loop.

    Some LEDDMX-style controllers do not advertise useful service UUIDs. So the
    auto-discovery path scans nearby BLE devices, skips obvious non-targets, then
    briefly connects to candidates and checks whether the FFE1 write
    characteristic exists after GATT discovery.
    """

    def __init__(
        self,
        address: str | None = None,
        *,
        config: LedDmxBluetoothConfig | None = None,
    ) -> None:
        if BleakClient is None or BleakScanner is None:
            raise BleakUnavailableError(
                "bleak is not installed. Install with: pip install bleak"
            )

        adapter_config = config or load_leddmx_config()

        self._address = (
            address.strip()
            if address is not None and address.strip()
            else None
        )
        self._service_uuid = adapter_config.service_uuid
        self._characteristic_uuid = adapter_config.characteristic_uuid
        self._excluded_service_uuids = set(
            adapter_config.excluded_service_uuids
        )
        self._excluded_name_fragments = (
            adapter_config.excluded_name_fragments
        )
        self._write_with_response = (
            adapter_config.write_with_response
        )
        self._command_delay_seconds = (
            adapter_config.command_delay_seconds
        )
        self._reconnect_delay_seconds = (
            adapter_config.reconnect_delay_seconds
        )
        self._scan_timeout_seconds = (
            adapter_config.scan_timeout_seconds
        )
        self._candidate_connect_timeout_seconds = (
            adapter_config.candidate_connect_timeout_seconds
        )

        self._loop = asyncio.new_event_loop()
        self._loop_ready = threading.Event()
        self._closed = False
        self._connected = False
        self._state = LightingState()
        self._state_lock = threading.Lock()

        self._client: BleakClient | None = None
        self._lock: asyncio.Lock | None = None

        self._thread = threading.Thread(
            target=self._run_loop,
            name="LedDmxBleLoop",
            daemon=True,
        )
        self._thread.start()
        self._loop_ready.wait(timeout=5.0)

    @property
    def is_connected(self) -> bool:
        return self.current_state().connected

    def current_state(self) -> LightingState:
        with self._state_lock:
            return self._state

    def connect(self) -> Future[None]:
        return self._submit(self._connect())

    def disconnect(self) -> Future[None]:
        return self._submit(self._disconnect())

    def close(self) -> None:
        if self._closed:
            return

        try:
            self.disconnect().result(timeout=2.0)
        except Exception:
            pass

        self._closed = True
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if (
            self._thread.is_alive()
            and threading.current_thread() is not self._thread
        ):
            self._thread.join(timeout=2.0)

        self._update_state(connected=False)

    def set_power(self, enabled: bool) -> Future[None]:
        return self._submit(
            self._write_and_update(
                LedDmxProtocol.power(enabled),
                power_enabled=bool(enabled),
            )
        )

    def set_color(self, color: RgbColor) -> Future[None]:
        return self._submit(
            self._write_and_update(
                LedDmxProtocol.color(color),
                color=color,
            )
        )

    def set_brightness(self, percent: int) -> Future[None]:
        value = max(0, min(percent, 100))
        return self._submit(
            self._write_and_update(
                LedDmxProtocol.brightness(value),
                brightness_percent=value,
            )
        )

    def set_color_temperature(self, percent: int) -> Future[None]:
        value = max(0, min(percent, 100))
        return self._submit(
            self._write_and_update(
                LedDmxProtocol.color_temperature(value),
                color_temperature_percent=value,
            )
        )

    def set_pattern(self, pattern_index: int) -> Future[None]:
        value = max(0, min(pattern_index, 210))
        return self._submit(
            self._write_and_update(
                LedDmxProtocol.pattern(value),
                pattern_index=value,
            )
        )

    def set_music_mode(self, eq_mode: int) -> Future[None]:
        value = max(0, min(eq_mode, 255))
        return self._submit(
            self._write_and_update(
                LedDmxProtocol.mic_eq(value),
                music_mode=value,
            )
        )

    def set_custom_pattern_mode(
        self,
        mode: CustomPatternMode,
    ) -> Future[None]:
        return self._submit(
            self._write_and_update(
                LedDmxProtocol.custom_pattern_mode(mode),
                custom_pattern_mode=mode,
            )
        )

    def set_custom_pattern_direction(
        self,
        is_forward: bool,
    ) -> Future[None]:
        return self._submit(
            self._write_and_update(
                LedDmxProtocol.custom_pattern_direction(is_forward),
                custom_pattern_forward=bool(is_forward),
            )
        )

    def _submit(self, coroutine: Coroutine[Any, Any, None]) -> Future[None]:
        if self._closed:
            future: Future[None] = Future()
            future.set_exception(RuntimeError("lighting controller is closed"))
            return future

        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()
        self._loop.run_forever()

        pending = asyncio.all_tasks(self._loop)
        for task in pending:
            task.cancel()
        if pending:
            self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self._loop.close()

    async def _ensure_loop_objects(self) -> None:
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def _connect(self) -> None:
        await self._ensure_loop_objects()
        assert self._lock is not None

        async with self._lock:
            await self._connect_unlocked()

    async def _disconnect(self) -> None:
        await self._ensure_loop_objects()
        assert self._lock is not None

        async with self._lock:
            if self._client is not None and self._client.is_connected:
                await self._client.disconnect()
            self._connected = False
            self._update_state(connected=False)

    async def _connect_unlocked(self) -> None:
        if self._client is not None and self._client.is_connected:
            self._connected = True
            return

        if self._address is not None:
            await self._connect_configured_address_unlocked()
            return

        self._client = await self._find_and_connect_leddmx_client()
        self._connected = bool(self._client.is_connected)
        self._update_state(connected=self._connected)

    async def _connect_configured_address_unlocked(self) -> None:
        assert BleakClient is not None

        if self._client is None:
            self._client = BleakClient(
                self._address,
                timeout=self._candidate_connect_timeout_seconds,
            )

        if not self._client.is_connected:
            await self._client.connect()

        if not self._client.services:
            raise RuntimeError(f"Connected to {self._address}, but no BLE services were discovered")

        if not self._client_has_leddmx_characteristic(self._client):
            await self._client.disconnect()
            self._connected = False
            raise RuntimeError(
                f"Device {self._address} does not expose LEDDMX characteristic "
                f"{self._characteristic_uuid}"
            )

        self._connected = bool(self._client.is_connected)
        self._update_state(connected=self._connected)

    async def _find_and_connect_leddmx_client(self) -> BleakClient:
        assert BleakClient is not None
        assert BleakScanner is not None

        discovered = await BleakScanner.discover(
            return_adv=True,
            timeout=self._scan_timeout_seconds,
        )

        candidates: list[tuple[BLEDevice, Any]] = []
        for device, advertisement in discovered.values():
            if self._is_obvious_non_lighting_device(device, advertisement):
                continue
            candidates.append((device, advertisement))

        candidates.sort(key=lambda item: getattr(item[1], "rssi", -999), reverse=True)

        errors: list[str] = []
        for device, advertisement in candidates:
            name = device.name or getattr(advertisement, "local_name", None) or "unnamed"
            rssi = getattr(advertisement, "rssi", None)

            client = BleakClient(device, timeout=self._candidate_connect_timeout_seconds)
            try:
                await client.connect()
                if self._client_has_leddmx_characteristic(client):
                    print(f"[Lighting] Found LEDDMX controller: {device.address} ({name}, RSSI={rssi})")
                    return client

                await client.disconnect()
                errors.append(f"{device.address} ({name}, RSSI={rssi}): no FFE1 characteristic")
            except Exception as exc:
                try:
                    if client.is_connected:
                        await client.disconnect()
                except Exception:
                    pass
                errors.append(f"{device.address} ({name}, RSSI={rssi}): {exc}")

        details = "; ".join(errors[:8]) if errors else "no BLE candidates discovered"
        raise RuntimeError(
            "LEDDMX lighting controller was not found. "
            "The scan completed, but no nearby BLE device exposed characteristic "
            f"{self._characteristic_uuid}. Tried: {details}"
        )

    def _is_obvious_non_lighting_device(self, device: BLEDevice, advertisement: Any) -> bool:
        name = (device.name or getattr(advertisement, "local_name", None) or "").lower()
        service_uuids = [uuid.lower() for uuid in getattr(advertisement, "service_uuids", [])]

        if any(
            fragment in name
            for fragment in self._excluded_name_fragments
        ):
            return True
        if any(uuid in self._excluded_service_uuids for uuid in service_uuids):
            return True
        return False

    def _client_has_leddmx_characteristic(self, client: BleakClient) -> bool:
        target = self._characteristic_uuid.lower()
        for service in client.services:
            for characteristic in service.characteristics:
                if characteristic.uuid.lower() == target:
                    return True
        return False

    async def _replace_client_from_scan(self) -> None:
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()

        if self._address is not None:
            self._client = None
            await self._connect_configured_address_unlocked()
            return

        self._client = await self._find_and_connect_leddmx_client()

    async def _write_and_update(
        self,
        packet: bytes,
        **state_changes: object,
    ) -> None:
        await self._write(packet)
        self._update_state(**state_changes)

    def _update_state(self, **changes: object) -> None:
        with self._state_lock:
            self._state = self._state.updated(**changes)

    async def _write(self, packet: bytes) -> None:
        await self._ensure_loop_objects()
        assert self._lock is not None

        async with self._lock:
            await self._connect_unlocked()
            assert self._client is not None

            try:
                await self._client.write_gatt_char(
                    self._characteristic_uuid,
                    packet,
                    response=self._write_with_response,
                )
            except Exception:
                self._connected = False
                if self._client.is_connected:
                    await self._client.disconnect()

                await asyncio.sleep(self._reconnect_delay_seconds)
                await self._replace_client_from_scan()
                assert self._client is not None
                await self._client.write_gatt_char(
                    self._characteristic_uuid,
                    packet,
                    response=self._write_with_response,
                )

            self._connected = bool(self._client.is_connected)
            self._update_state(connected=self._connected)
            if self._command_delay_seconds > 0:
                await asyncio.sleep(self._command_delay_seconds)
