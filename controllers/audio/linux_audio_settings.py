# SPDX-License-Identifier: MIT
"""Linux playback output selection and BlueZ receiver operations."""

import json
import re
import subprocess
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

from ui.system.audio_settings_if import AudioAction, AudioDevice, AudioSettingsState
from ui.ui_dispatcher_if import UiDispatcherIf

_ADDRESS = re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}")
_AUDIO_SINK = "0000110b-0000-1000-8000-00805f9b34fb"


class LinuxAudioSettings:
    """Serialize bounded audio commands and publish results on the UI thread."""

    def __init__(self, dispatcher: UiDispatcherIf) -> None:
        self._dispatcher = dispatcher
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="orc-audio-settings")
        self._closed = False
        self._bluetooth_timer: object | None = None

    @staticmethod
    def _run(*command: str, timeout: int = 5) -> str:
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=True, timeout=timeout
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"{command[0]} is unavailable. Install the ORC audio features."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"{command[0]} timed out.") from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() or exc.stdout.strip()
            raise RuntimeError(f"{command[0]}: {detail or 'operation failed'}") from exc
        return result.stdout.strip()

    def _outputs(self) -> tuple[AudioDevice, ...]:
        sinks = json.loads(self._run("pactl", "-f", "json", "list", "sinks"))
        selected = self._run("pactl", "get-default-sink") if sinks else ""
        return tuple(
            AudioDevice(
                sink["name"], sink.get("description") or sink["name"], sink["name"] == selected
            )
            for sink in sinks
        )

    def _receivers(self) -> tuple[AudioDevice, ...]:
        receivers = []
        for line in self._run("bluetoothctl", "devices").splitlines():
            tokens = line.split(maxsplit=2)
            if len(tokens) != 3 or tokens[0] != "Device" or not _ADDRESS.fullmatch(tokens[1]):
                continue
            _, address, name = tokens
            try:
                details = self._run("bluetoothctl", "info", address)
            except RuntimeError:
                # A scan result can expire before BlueZ answers the detail query.
                continue
            fields = {text.strip() for text in details.splitlines()}
            if _AUDIO_SINK in details.lower() or fields.intersection(
                {
                    "Icon: audio-card",
                    "Icon: audio-headphones",
                    "Icon: audio-headset",
                    "Icon: audio-speakers",
                }
            ):
                receivers.append(
                    AudioDevice(address, name, "Connected: yes" in fields, "Paired: yes" in fields)
                )
        return tuple(receivers)

    def _snapshot(self) -> AudioSettingsState:
        warnings = []
        try:
            outputs = self._outputs()
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            outputs = ()
            warnings.append(f"Playback outputs: {exc}")
        try:
            receivers = self._receivers()
        except RuntimeError as exc:
            receivers = ()
            warnings.append(f"Bluetooth: {exc}")
        return AudioSettingsState(outputs, receivers, tuple(warnings))

    def _perform(self, action: AudioAction, identifier: str) -> AudioSettingsState:
        if action is AudioAction.SELECT_OUTPUT:
            if identifier not in {device.identifier for device in self._outputs()}:
                raise RuntimeError("That playback output is no longer available. Refresh the list.")
            self._run("pactl", "set-default-sink", identifier)
        elif action is AudioAction.SCAN:
            self._run("bluetoothctl", "--timeout", "8", "scan", "on", timeout=12)
        elif action in (AudioAction.CONNECT, AudioAction.DISCONNECT):
            receivers = {device.identifier: device for device in self._receivers()}
            receiver = receivers.get(identifier)
            if receiver is None:
                raise RuntimeError("The Bluetooth receiver is unavailable. Scan again.")
            if action is AudioAction.CONNECT and not receiver.paired:
                try:
                    self._run("bluetoothctl", "--timeout", "15", "pair", identifier, timeout=18)
                except RuntimeError as exc:
                    raise RuntimeError(
                        f"Pairing failed: {exc}. If a PIN is required, pair in the Pi's Bluetooth settings."
                    ) from exc
                details = self._run("bluetoothctl", "info", identifier)
                if "Connected: yes" in {line.strip() for line in details.splitlines()}:
                    return self._snapshot()
            command = "connect" if action is AudioAction.CONNECT else "disconnect"
            self._run("bluetoothctl", "--timeout", "12", command, identifier, timeout=16)
        return self._snapshot()

    def request(
        self,
        action: AudioAction,
        identifier: str,
        on_result: Callable[[AudioSettingsState], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Run the request away from Tk and dispatch the resulting state."""
        if self._closed:
            return

        def complete(result: Future[AudioSettingsState]) -> None:
            def deliver() -> None:
                if self._closed:
                    return
                try:
                    state = result.result()
                except (RuntimeError, OSError, ValueError, TypeError, KeyError) as exc:
                    on_error(str(exc))
                else:
                    on_result(state)

            self._dispatcher.dispatch_ui(deliver)

        self._executor.submit(self._perform, action, identifier).add_done_callback(complete)

    def monitor_bluetooth(self, on_status: Callable[[bool], None]) -> None:
        """Observe BlueZ connection state while the settings controller is open."""
        def probe() -> bool:
            output = self._run("bluetoothctl", "devices", "Connected")
            return any(
                len(parts) >= 2 and parts[0] == "Device" and _ADDRESS.fullmatch(parts[1])
                for parts in (line.split(maxsplit=2) for line in output.splitlines())
            )

        def poll() -> None:
            self._bluetooth_timer = None
            if not self._closed:
                self._executor.submit(probe).add_done_callback(complete)

        def complete(result: Future[bool]) -> None:
            def deliver() -> None:
                if self._closed:
                    return
                try:
                    connected = result.result()
                except (OSError, RuntimeError):
                    connected = False
                on_status(connected)
                self._bluetooth_timer = self._dispatcher.schedule_ui_callback(5000, poll)

            self._dispatcher.dispatch_ui(deliver)

        poll()

    def close(self) -> None:
        """Discard queued requests and late results during shutdown."""
        self._closed = True
        if self._bluetooth_timer is not None:
            self._dispatcher.cancel_ui_callback(self._bluetooth_timer)
            self._bluetooth_timer = None
        self._executor.shutdown(wait=False, cancel_futures=True)
