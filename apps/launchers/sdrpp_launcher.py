# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import os
import shlex
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from apps.launchers.app_launcher_if import AppLauncherIf, StatusCallback
from apps.launchers.process_manager import close_matching_display_apps, is_process_running, terminate_process
from common.logging.logging_paths import logging_file_path
from protocols.sdrpp_remote_control import SDRPPRemoteControlClient

DEFAULT_TERMUX_SDRPP_SOURCE = Path("/root/SDRPlusPlus")
DEFAULT_TERMUX_PROOT_DISTRIBUTION = "debian"
DEFAULT_TERMUX_XDG_RUNTIME_DIR = "/tmp/runtime-root"
DEFAULT_NATIVE_SDRPP_ROOT = Path.home() / "SDRPlusPlus" / "root_dev"
DEFAULT_REMOTE_CONTROL_HOST = "127.0.0.1"
DEFAULT_REMOTE_CONTROL_PORT = 4533
_VALID_THEMES = {"Dark", "Light"}
_THEME_SYNC_LOCK = threading.Lock()
_PENDING_THEME_SYNC: tuple[str, str, Path, Path | None] | None = None
_THEME_SYNC_WATCHER_RUNNING = False


@dataclass(frozen=True, slots=True)
class SDRPPProfile:
    """Define SDR++ startup mode, tuning step, and optional frequency."""
    name: str
    mode: str
    step_hz: int
    start_frequency_hz: int | None = None


class SDRPPLauncher(AppLauncherIf):
    """Launch SDR++ and expose its RF and application-control endpoints."""

    def __init__(self, *, profile: SDRPPProfile, log_file: str | Path | None = None, fullscreen: bool = True, embedded: bool = False, resource_manager=None, owner_name: str = "sdrpp", rigctl_host: str = "127.0.0.1", rigctl_port: int = 4532, rigctl_timeout_seconds: float = 15.0, remote_control_host: str = DEFAULT_REMOTE_CONTROL_HOST, remote_control_port: int = DEFAULT_REMOTE_CONTROL_PORT, remote_control_timeout_seconds: float = 0.75, termux_proot_distribution: str = DEFAULT_TERMUX_PROOT_DISTRIBUTION, termux_sdrpp_source: str | Path = DEFAULT_TERMUX_SDRPP_SOURCE, theme: str | None = None) -> None:
        self.profile = profile
        self.log_file = Path(log_file or logging_file_path("openroadcode", "sdrpp.log"))
        self.fullscreen = fullscreen
        self.embedded = embedded
        self.resource_manager = resource_manager
        self.owner_name = owner_name
        self.rigctl_host = rigctl_host
        self.rigctl_port = rigctl_port
        self.rigctl_timeout_seconds = rigctl_timeout_seconds
        self.remote_control = SDRPPRemoteControlClient(host=remote_control_host, port=remote_control_port, timeout=remote_control_timeout_seconds)
        self.termux_proot_distribution = termux_proot_distribution
        self.termux_sdrpp_source = Path(termux_sdrpp_source)
        self.theme = _normalize_theme(theme) if theme is not None else None
        self._process: subprocess.Popen[str] | None = None
        self._launched_via_proot = False

    def is_running(self) -> bool:
        if self._process is not None:
            if self._process.poll() is None:
                return True
            self._process = None
        return _sdrpp_process_running()

    def set_theme(self, theme: str) -> bool:
        self.theme = _normalize_theme(theme)
        if self.is_running():
            try:
                if self.remote_control.set_theme(self.theme):
                    return True
            except (OSError, RuntimeError):
                pass
        return self.sync_theme()

    def sync_theme(self) -> bool:
        if self.theme is None:
            return False
        return sync_sdrpp_theme(self.theme, termux_proot_distribution=self.termux_proot_distribution, termux_sdrpp_source=self.termux_sdrpp_source, remote_control=self.remote_control)

    def launch(self, remote_display: str, set_status: StatusCallback = None) -> None:
        if self.resource_manager is not None:
            self.resource_manager.acquire(self.owner_name, force=True, set_status=set_status)
        _stop_readsb_service()

        if self.is_running():
            if self.is_rigctl_ready():
                _status(set_status, f"SDR++ already ready: {self.profile.name}")
                return
            # A process without the endpoint required by the radio contract is
            # not reusable. Waiting here used to strand ORC behind a stale or
            # half-started SDR++ process. Recover it and launch a clean instance.
            _status(set_status, "Recovering SDR++ without RigCTL...")
            self.stop(remote_display, set_status)
            time.sleep(0.25)

        if self.theme is not None:
            self.sync_theme()

        command = self._launch_command(remote_display)
        self._launched_via_proot = _is_proot_command(command)
        environment = _sdrpp_environment(remote_display)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = self.log_file.open("a", encoding="utf-8")
        try:
            self._process = subprocess.Popen(command, env=environment, stdout=log_handle, stderr=subprocess.STDOUT, start_new_session=True, text=True)
        finally:
            log_handle.close()

        if self.fullscreen and not self.embedded:
            self._request_fullscreen(remote_display, environment)
        mode = "embedded" if self.embedded else "standalone"
        _status(set_status, f"SDR++ launched ({mode}); waiting for RigCTL...")
        self.wait_for_rigctl()
        _status(set_status, f"SDR++ ready: {self.profile.name}")

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        if self._process is not None:
            terminate_process(self._process)
            self._process = None
        self._launched_via_proot = False
        close_matching_display_apps(display=remote_display, patterns=("sdrpp", "sdr\\+\\+"))
        _status(set_status, "SDR++ stopped")

    def toggle(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        if self.is_running():
            self.stop(remote_display, set_status)
            return False
        self.launch(remote_display, set_status)
        return True

    def window_process_id(self, timeout_seconds: float = 8.0) -> int:
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("SDR++ is not running under this launcher")
        if not self._launched_via_proot:
            return self._process.pid
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            pid = _find_descendant_matching(self._process.pid, ("./build/sdrpp", "/build/sdrpp", "SDRPlusPlus"))
            if pid is not None:
                return pid
            time.sleep(0.1)
        raise RuntimeError("Could not find SDR++ child process inside proot")

    def is_rigctl_ready(self) -> bool:
        try:
            with socket.create_connection((self.rigctl_host, self.rigctl_port), timeout=0.5):
                return True
        except OSError:
            return False

    def is_remote_control_ready(self) -> bool:
        return self.remote_control.ping()

    def wait_for_rigctl(self) -> None:
        deadline = time.monotonic() + self.rigctl_timeout_seconds
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(f"SDR++ exited before RigCTL became ready. Check log: {self.log_file}")
            try:
                with socket.create_connection((self.rigctl_host, self.rigctl_port), timeout=0.5):
                    return
            except OSError as exc:
                last_error = exc
                time.sleep(0.5)
        raise RuntimeError(f"RigCTL did not become ready at {self.rigctl_host}:{self.rigctl_port}: {last_error}")

    def _launch_command(self, display: str) -> list[str]:
        executable = shutil.which("sdrpp") or shutil.which("sdr++")
        if executable is not None:
            return [executable, "--autostart"]
        if not _is_termux():
            raise RuntimeError("Could not find sdrpp or sdr++ in PATH")
        proot_distro = shutil.which("proot-distro")
        if proot_distro is None:
            raise RuntimeError("Could not find native SDR++ or proot-distro on Termux")
        source = str(self.termux_sdrpp_source)
        runtime_dir = DEFAULT_TERMUX_XDG_RUNTIME_DIR
        shell_command = f"mkdir -p {shlex.quote(runtime_dir)} && chmod 700 {shlex.quote(runtime_dir)} && cd {shlex.quote(source)} && exec ./build/sdrpp -r root_dev --autostart"
        return [proot_distro, "login", self.termux_proot_distribution, "--shared-tmp", "--", "env", f"DISPLAY={display}", f"XDG_RUNTIME_DIR={runtime_dir}", "XDG_SESSION_TYPE=x11", "GDK_BACKEND=x11", "LIBGL_ALWAYS_SOFTWARE=1", "bash", "-lc", shell_command]

    def _request_fullscreen(self, display: str, environment: dict[str, str]) -> None:
        subprocess.Popen(["bash", "-lc", f'sleep 3; DISPLAY="{display}" wmctrl -r "SDR++" -b add,fullscreen'], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True, text=True)


def sync_sdrpp_theme(theme: str, *, termux_proot_distribution: str = DEFAULT_TERMUX_PROOT_DISTRIBUTION, termux_sdrpp_source: str | Path = DEFAULT_TERMUX_SDRPP_SOURCE, native_root: str | Path | None = None, remote_control: SDRPPRemoteControlClient | None = None) -> bool:
    selected = _normalize_theme(theme)
    source = Path(termux_sdrpp_source)
    root = Path(native_root) if native_root is not None else None
    if _sdrpp_process_running():
        client = remote_control or SDRPPRemoteControlClient()
        try:
            if client.set_theme(selected):
                return True
        except (OSError, RuntimeError):
            pass
        _defer_sdrpp_theme_sync(selected, termux_proot_distribution, source, root)
        return True
    return _write_sdrpp_theme(selected, termux_proot_distribution=termux_proot_distribution, termux_sdrpp_source=source, native_root=root)


def _defer_sdrpp_theme_sync(theme: str, termux_proot_distribution: str, termux_sdrpp_source: Path, native_root: Path | None) -> None:
    global _PENDING_THEME_SYNC, _THEME_SYNC_WATCHER_RUNNING
    with _THEME_SYNC_LOCK:
        _PENDING_THEME_SYNC = (theme, termux_proot_distribution, termux_sdrpp_source, native_root)
        if _THEME_SYNC_WATCHER_RUNNING:
            return
        _THEME_SYNC_WATCHER_RUNNING = True
    threading.Thread(target=_theme_sync_worker, name="sdrpp-theme-sync", daemon=True).start()


def _theme_sync_worker() -> None:
    global _PENDING_THEME_SYNC, _THEME_SYNC_WATCHER_RUNNING
    while _sdrpp_process_running():
        time.sleep(0.25)
    with _THEME_SYNC_LOCK:
        pending = _PENDING_THEME_SYNC
        _PENDING_THEME_SYNC = None
        _THEME_SYNC_WATCHER_RUNNING = False
    if pending is None:
        return
    theme, distribution, source, native_root = pending
    _write_sdrpp_theme(theme, termux_proot_distribution=distribution, termux_sdrpp_source=source, native_root=native_root)


def _write_sdrpp_theme(theme: str, *, termux_proot_distribution: str, termux_sdrpp_source: Path, native_root: Path | None) -> bool:
    if _is_termux():
        proot_distro = shutil.which("proot-distro")
        if proot_distro is None:
            return False
        config_path = termux_sdrpp_source / "root_dev" / "config.json"
        script = "import json, pathlib, sys; p=pathlib.Path(sys.argv[1]); d=json.loads(p.read_text()); d['theme']=sys.argv[2]; p.write_text(json.dumps(d, indent=4)+'\\n')"
        result = subprocess.run([proot_distro, "login", termux_proot_distribution, "--shared-tmp", "--", "python3", "-c", script, str(config_path), theme], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    root = native_root if native_root is not None else DEFAULT_NATIVE_SDRPP_ROOT
    config_path = root / "config.json"
    if not config_path.is_file():
        return False
    try:
        document = json.loads(config_path.read_text(encoding="utf-8"))
        document["theme"] = theme
        config_path.write_text(json.dumps(document, indent=4) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        return False
    return True


def _sdrpp_process_running() -> bool:
    return is_process_running("sdrpp") or is_process_running("sdr\\+\\+")


def _normalize_theme(theme: str) -> str:
    selected = theme.strip().capitalize()
    if selected not in _VALID_THEMES:
        raise ValueError(f"Unsupported SDR++ theme: {theme!r}")
    return selected


def _is_proot_command(command: list[str]) -> bool:
    return bool(command and Path(command[0]).name == "proot-distro")


def _find_descendant_matching(root_pid: int, command_fragments: tuple[str, ...]) -> int | None:
    try:
        result = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True, check=False)
    except OSError:
        return None
    children: dict[int, list[int]] = {}
    commands: dict[int, str] = {}
    for line in result.stdout.splitlines():
        fields = line.strip().split(maxsplit=2)
        if len(fields) < 3 or not fields[0].isdigit() or not fields[1].isdigit():
            continue
        pid, parent_pid, command = int(fields[0]), int(fields[1]), fields[2]
        children.setdefault(parent_pid, []).append(pid)
        commands[pid] = command
    pending = list(children.get(root_pid, ()))
    while pending:
        pid = pending.pop(0)
        command = commands.get(pid, "")
        if any(fragment in command for fragment in command_fragments):
            return pid
        pending.extend(children.get(pid, ()))
    return None


def _sdrpp_environment(remote_display: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment["DISPLAY"] = remote_display
    environment.pop("LD_PRELOAD", None)
    return environment


def _stop_readsb_service() -> None:
    if not _is_termux():
        return
    sv = shutil.which("sv")
    if sv is None:
        return
    subprocess.run([sv, "down", "readsb"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def _is_termux() -> bool:
    prefix = os.getenv("PREFIX", "")
    return bool(os.getenv("TERMUX_VERSION")) or prefix.startswith("/data/data/com.termux/")


def _status(callback: StatusCallback, message: str) -> None:
    if callback is not None:
        callback(message)
