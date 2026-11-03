"""Waydroid-backed Android application launcher."""

from __future__ import annotations

import shutil
import subprocess
import re
from dataclasses import dataclass


class WaydroidLauncherError(RuntimeError):
    """Raised when Waydroid cannot satisfy an application request."""


@dataclass(frozen=True)
class AndroidApp:
    """An Android application exposed by Waydroid."""

    name: str
    package: str


class WaydroidLauncher:
    """Start and inspect Android applications exposed by Waydroid."""

    def __init__(self, executable: str = "waydroid") -> None:
        self._executable = executable

    def is_available(self) -> bool:
        if shutil.which(self._executable) is None:
            return False

        try:
            result = subprocess.run(
                [self._executable, "status"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False

        return result.returncode == 0

    def list_apps(self) -> tuple[AndroidApp, ...]:
        result = self._run("app", "list")
        apps: list[AndroidApp] = []
        name: str | None = None
        package: str | None = None

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if line.startswith("Name:"):
                name = line.partition(":")[2].strip()
            elif line.startswith("packageName:"):
                package = line.partition(":")[2].strip()

            if name and package:
                apps.append(AndroidApp(name=name, package=package))
                name = None
                package = None

        return tuple(apps)

    def launch_app(self, package: str) -> None:
        package = package.strip()
        if not package:
            raise ValueError("Android package name must not be empty")
        self._run("app", "launch", package)

    def launch_uri(self, uri: str) -> None:
        """Use Waydroid's session service for an Android VIEW deep link."""
        result = self._run('app', 'intent', 'android.intent.action.VIEW', uri)
        if 'Failed to access IPlatform service' in result.stdout + result.stderr:
            raise WaydroidLauncherError('Waydroid could not deliver the destination intent')

    def stop_app(self, package: str) -> None:
        """Explicit user close, targeted to this local Waydroid instance only."""
        status = self._run('status').stdout
        address = re.search(r'^\s*IP address:\s*(\d+\.\d+\.\d+\.\d+)\s*$', status, re.MULTILINE)
        if address is None:
            raise WaydroidLauncherError('The local Waydroid session has no IP address')
        self._run('adb', 'connect')
        serial = address[1] + ':5555'
        try:
            model = subprocess.run(['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model'],
                                   capture_output=True, text=True, timeout=5, check=True)
            if 'waydroid' not in model.stdout.casefold():
                raise WaydroidLauncherError('The selected device is not Waydroid')
            result = subprocess.run(['adb', '-s', serial, 'shell', 'am', 'force-stop', package],
                                   capture_output=True, text=True, timeout=5, check=True)
            if 'Exception' in result.stdout + result.stderr or 'Error:' in result.stdout + result.stderr:
                raise WaydroidLauncherError('Android refused to stop Waze')
        except (OSError, subprocess.SubprocessError) as error:
            raise WaydroidLauncherError('Could not stop the app in the local Waydroid session') from error

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        if shutil.which(self._executable) is None:
            raise WaydroidLauncherError(
                f"Waydroid executable not found: {self._executable}"
            )

        try:
            result = subprocess.run(
                [self._executable, *arguments],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise WaydroidLauncherError(f"Waydroid request failed: {exc}") from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise WaydroidLauncherError(
                f"Waydroid command failed ({result.returncode}): {detail}"
            )
        return result
