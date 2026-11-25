# SPDX-License-Identifier: MIT
"""Configure the current user's graphical-session OpenRoadCode launcher."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


def desktop_exec_arg(value: str) -> str:
    """Quote a literal argument for a Desktop Entry Exec key."""
    if any(character in value for character in "\r\n"):
        raise ValueError("Desktop launcher paths cannot contain line breaks")
    # Desktop Entry value decoding happens before Exec argument decoding.
    escaped = value.replace("%", "%%").replace("\\", "\\\\\\\\")
    for character in ('"', "$", "`"):
        escaped = escaped.replace(character, "\\\\" + character)
    return f'"{escaped}"'


def configure_autostart(entry: Path, *, enabled: bool, launcher: Path, python: Path) -> None:
    """Install or remove the installer-owned entry."""
    if not enabled:
        entry.unlink(missing_ok=True)
        return

    for executable in (launcher, python):
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError(f"Autostart executable unavailable: {executable}")

    command = " ".join(
        desktop_exec_arg(value) for value in ("/usr/bin/env", f"PYTHON={python}", str(launcher))
    )
    entry.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=entry.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=OpenRoadCode\n"
                f"Exec={command}\n"
                "Terminal=false\n"
            )
            stream.close()
            temporary.replace(entry)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", choices=("enable", "disable"))
    parser.add_argument("launcher", type=Path)
    parser.add_argument("python", type=Path)
    args = parser.parse_args()

    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    entry = config / "autostart" / "openroadcode-orcui.desktop"
    try:
        # Absolute paths are needed at login. Preserve the virtualenv symlink.
        configure_autostart(
            entry,
            enabled=args.state == "enable",
            launcher=args.launcher.absolute(),
            python=args.python.absolute(),
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"[!] Could not configure ORC autostart: {exc}\n")
    print(f"[+] ORC graphical-session autostart: {args.state}d")


if __name__ == "__main__":
    main()
