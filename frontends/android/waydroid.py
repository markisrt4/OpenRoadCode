"""Waydroid-backed Android application frontend."""

from __future__ import annotations

import shutil
import subprocess

from .android_app_launcher import AndroidApp, AndroidAppLauncher, AndroidAppLauncherError


class WaydroidAppLauncher(AndroidAppLauncher):
    """Expose Waydroid applications through the Android frontend contract."""

    def __init__(self, executable: str = "waydroid") -> None:
        self._executable = executable

    def is_available(self) -> bool:
        if shutil.which(self._executable) is None:
            return False

        result = subprocess.run(
            [self._executable, "status"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def list_apps(self) -> tuple[AndroidApp, ...]:
        result = self._run("app", "list")
        apps: list[AndroidApp] = []

        # Waydroid prints application records as Name:/packageName: fields.
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

    def launch(self, package: str) -> None:
        package = package.strip()
        if not package:
            raise ValueError("Android package name must not be empty")
        self._run("app", "launch", package)

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        if shutil.which(self._executable) is None:
            raise AndroidAppLauncherError(
                f"Android runtime executable not found: {self._executable}"
            )

        result = subprocess.run(
            [self._executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise AndroidAppLauncherError(
                f"Waydroid command failed ({result.returncode}): {detail}"
            )
        return result
