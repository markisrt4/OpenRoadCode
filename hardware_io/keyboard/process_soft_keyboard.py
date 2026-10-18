# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Own an explicitly configured foreground system keyboard process."""
from collections.abc import Sequence
import os
import shutil
import subprocess

from hardware_io.keyboard.soft_keyboard_if import SoftKeyboardIf


class ProcessSoftKeyboard(SoftKeyboardIf):
    """Use an installed non-focus-stealing keyboard; never install or kill by name.

    The configured command must stay in the foreground and own a keyboard window.
    Daemons and commands controlling an independently owned keyboard need their own
    adapter. Construction neither probes devices nor launches any application.
    """

    def __init__(self, command: Sequence[str], *, display: str | None = None) -> None:
        if isinstance(command, (str, bytes)) or not command or any(
            not isinstance(part, str) or not part or '\0' in part for part in command
        ):
            raise ValueError('Keyboard command must be a nonempty argument sequence')
        self._command = tuple(command)
        self._display = display
        self._process: subprocess.Popen[bytes] | None = None
        self._closed = False

    @property
    def available(self) -> bool:
        return not self._closed and shutil.which(self._command[0]) is not None

    def show(self) -> None:
        if self._closed:
            raise RuntimeError('Keyboard adapter is closed')
        if self._process is not None and self._process.poll() is None:
            return
        executable = shutil.which(self._command[0])
        if executable is None:
            raise RuntimeError('Configured system keyboard is not installed')
        environment = os.environ.copy()
        if self._display is not None:
            environment['DISPLAY'] = self._display
        self._process = subprocess.Popen(
            (executable, *self._command[1:]), env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if self._process.poll() is not None:
            self._process = None
            raise RuntimeError('System keyboard exited during startup')

    def hide(self) -> None:
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                process.wait(timeout=0.5)
        self._process = None

    def close(self) -> None:
        self._closed = True
        self.hide()
