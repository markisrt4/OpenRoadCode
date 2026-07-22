from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

from evdev import InputDevice, categorize, ecodes, list_devices


LOGGER = logging.getLogger(__name__)

KeyCallback = Callable[[str], None]


class KeyboardReader:
    """
    Reads key-press events from a Linux input device.

    The reader reports Linux key names such as:

        KEY_LEFT
        KEY_RIGHT
        KEY_ENTER
        KEY_SPACE
        KEY_VOLUMEUP

    It does not assign application-specific meaning to those keys.
    """

    def __init__(
        self,
        device_path: str | None = None,
        callback: KeyCallback | None = None,
    ) -> None:
        """
        Args:
            device_path:
                Linux input device path, such as ``/dev/input/event3``.

                When omitted, the reader attempts to locate a keyboard-like
                input device automatically.

            callback:
                Optional function called whenever a key is pressed.
        """
        if callback is not None and not callable(callback):
            raise TypeError("callback must be callable")

        self._device_path = device_path
        self._callback = callback

        self._device: InputDevice | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def device_path(self) -> str | None:
        return self._device_path

    @property
    def device_name(self) -> str | None:
        if self._device is None:
            return None

        return self._device.name

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def open(self) -> None:
        """
        Opens the configured input device.

        If no device path was supplied, a keyboard-like device is selected
        automatically.
        """
        if self._device is not None:
            return

        if self._device_path is None:
            self._device_path = self.find_keyboard_device()

        path = Path(self._device_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Keyboard input device does not exist: {self._device_path}"
            )

        self._device = InputDevice(self._device_path)

        LOGGER.info(
            "Opened keyboard device %s (%s)",
            self._device.path,
            self._device.name,
        )

    def close(self) -> None:
        """
        Closes the input device.
        """
        if self.is_running:
            self.stop()

        if self._device is not None:
            self._device.close()
            self._device = None

    def read_keys(self) -> Iterator[str]:
        """
        Blocks and yields key names whenever a key is pressed.

        Example:

            for key in reader.read_keys():
                print(key)
        """
        self.open()

        if self._device is None:
            raise RuntimeError("Keyboard device is not open")

        for event in self._device.read_loop():
            if event.type != ecodes.EV_KEY:
                continue

            key_event = categorize(event)

            if key_event.keystate != key_event.key_down:
                continue

            yield self._normalize_keycode(key_event.keycode)

    def start(self, callback: KeyCallback | None = None) -> None:
        """
        Starts reading keyboard events in a background thread.

        Args:
            callback:
                Optional callback override. If omitted, the callback supplied
                to the constructor is used.
        """
        if callback is not None:
            if not callable(callback):
                raise TypeError("callback must be callable")

            self._callback = callback

        if self._callback is None:
            raise ValueError("A callback is required before starting")

        if self.is_running:
            return

        self.open()
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="KeyboardReader",
            daemon=True,
        )
        self._thread.start()

        LOGGER.info("Keyboard reader started")

    def stop(self) -> None:
        """
        Stops the background reader.
        """
        self._stop_event.set()

        if self._device is not None:
            self._device.close()
            self._device = None

        if (
            self._thread is not None
            and self._thread.is_alive()
            and self._thread is not threading.current_thread()
        ):
            self._thread.join(timeout=1.0)

        self._thread = None

        LOGGER.info("Keyboard reader stopped")

    def _run(self) -> None:
        try:
            for key in self.read_keys():
                if self._stop_event.is_set():
                    break

                callback = self._callback

                if callback is not None:
                    callback(key)

        except OSError:
            if not self._stop_event.is_set():
                LOGGER.exception("Keyboard input device failed")

        except Exception:
            LOGGER.exception("Unexpected keyboard reader failure")

    @staticmethod
    def _normalize_keycode(keycode: str | list[str]) -> str:
        """Returns one key name when evdev reports aliases for a keycode."""
        if isinstance(keycode, str):
            return keycode

        if not keycode:
            raise ValueError("Keyboard event did not contain a keycode")

        return keycode[0]

    @staticmethod
    def find_keyboard_device() -> str:
        """
        Returns the first keyboard-like Linux input device.

        A device is considered keyboard-like when it supports common keyboard
        keys such as letters, Enter, or Space.
        """
        keyboard_keys = {
            ecodes.KEY_A,
            ecodes.KEY_ENTER,
            ecodes.KEY_SPACE,
        }

        candidates: list[InputDevice] = []

        try:
            for path in list_devices():
                device = InputDevice(path)
                candidates.append(device)

                capabilities = device.capabilities()
                supported_keys = set(capabilities.get(ecodes.EV_KEY, []))

                if keyboard_keys.issubset(supported_keys):
                    selected_path = device.path

                    for candidate in candidates:
                        candidate.close()

                    return selected_path

        finally:
            for device in candidates:
                try:
                    device.close()
                except OSError:
                    pass

        raise RuntimeError("No keyboard-like input device was found")
