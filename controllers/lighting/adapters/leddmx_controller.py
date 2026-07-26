from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any

from controllers.lighting.lighting_controller_if import LightingControllerIf
from controllers.lighting.lighting_types import (
    CustomPatternMode,
    LightingConnectionStatus,
    LightingState,
    RgbColor,
)
from hardware_io.bluetooth import (
    BleGattState,
    BleGattStatus,
    BleGattTransportIf,
)
from protocols.leddmx import LedDmxProtocol


_STATUS_MAP = {
    BleGattStatus.DISCONNECTED: LightingConnectionStatus.DISCONNECTED,
    BleGattStatus.CONNECTING: LightingConnectionStatus.CONNECTING,
    BleGattStatus.CONNECTED: LightingConnectionStatus.CONNECTED,
    BleGattStatus.RECONNECTING: LightingConnectionStatus.RECONNECTING,
    BleGattStatus.ERROR: LightingConnectionStatus.ERROR,
}


class LedDmxController(LightingControllerIf):
    """Translate generic lighting operations into LEDDMX transport writes.

    Bluetooth discovery, GATT connection lifecycle, and retry behavior are
    delegated to the injected transport.
    """

    def __init__(self, transport: BleGattTransportIf) -> None:
        self._transport = transport
        transport_state = transport.current_state()
        self._state = LightingState(
            connection_status=_STATUS_MAP[transport_state.status],
            device_address=transport_state.address,
            last_connection_error=transport_state.last_error,
        )
        self._state_lock = threading.Lock()
        self._closed = False

        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="LedDmxControllerLoop",
            daemon=True,
        )
        self._thread.start()
        self._loop_ready.wait(timeout=5.0)

    @property
    def is_connected(self) -> bool:
        return self.current_state().connected

    def current_state(self) -> LightingState:
        self._synchronize_transport_state()
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
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if (
            self._thread.is_alive()
            and threading.current_thread() is not self._thread
        ):
            self._thread.join(timeout=2.0)
        self._synchronize_transport_state()

    def set_power(self, enabled: bool) -> Future[None]:
        return self._command(
            LedDmxProtocol.power(enabled),
            power_enabled=bool(enabled),
        )

    def set_color(self, color: RgbColor) -> Future[None]:
        return self._command(LedDmxProtocol.color(color), color=color)

    def set_brightness(self, percent: int) -> Future[None]:
        value = max(0, min(percent, 100))
        return self._command(
            LedDmxProtocol.brightness(value),
            brightness_percent=value,
        )

    def set_color_temperature(self, percent: int) -> Future[None]:
        value = max(0, min(percent, 100))
        return self._command(
            LedDmxProtocol.color_temperature(value),
            color_temperature_percent=value,
        )

    def set_pattern(self, pattern_index: int) -> Future[None]:
        value = max(0, min(pattern_index, 210))
        return self._command(
            LedDmxProtocol.pattern(value),
            pattern_index=value,
        )

    def set_music_mode(self, eq_mode: int) -> Future[None]:
        value = max(0, min(eq_mode, 255))
        return self._command(
            LedDmxProtocol.mic_eq(value),
            music_mode=value,
        )

    def set_custom_pattern_mode(
        self,
        mode: CustomPatternMode,
    ) -> Future[None]:
        return self._command(
            LedDmxProtocol.custom_pattern_mode(mode),
            custom_pattern_mode=mode,
        )

    def set_custom_pattern_direction(
        self,
        is_forward: bool,
    ) -> Future[None]:
        return self._command(
            LedDmxProtocol.custom_pattern_direction(is_forward),
            custom_pattern_forward=bool(is_forward),
        )

    def _command(self, packet: bytes, **changes: object) -> Future[None]:
        return self._submit(self._write_and_update(packet, **changes))

    async def _connect(self) -> None:
        try:
            await self._transport.connect()
        finally:
            self._synchronize_transport_state()

    async def _disconnect(self) -> None:
        try:
            await self._transport.disconnect()
        finally:
            self._synchronize_transport_state()

    async def _write_and_update(
        self,
        packet: bytes,
        **changes: object,
    ) -> None:
        try:
            await self._transport.write(packet)
        finally:
            self._synchronize_transport_state()
        with self._state_lock:
            self._state = self._state.updated(**changes)

    def _synchronize_transport_state(self) -> None:
        transport_state = self._transport.current_state()
        self._apply_transport_state(transport_state)

    def _apply_transport_state(self, transport_state: BleGattState) -> None:
        with self._state_lock:
            self._state = self._state.updated(
                connection_status=_STATUS_MAP[transport_state.status],
                device_address=transport_state.address,
                last_connection_error=transport_state.last_error,
            )

    def _submit(self, coroutine: Coroutine[Any, Any, None]) -> Future[None]:
        if self._closed:
            coroutine.close()
            future: Future[None] = Future()
            future.set_exception(RuntimeError("lighting controller is closed"))
            return future
        self._loop_ready.wait(timeout=5.0)
        if self._loop is None or not self._loop.is_running():
            coroutine.close()
            future = Future()
            future.set_exception(
                RuntimeError("lighting controller event loop is unavailable")
            )
            return future
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        self._loop_ready.set()
        loop.run_forever()
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
        loop.close()
