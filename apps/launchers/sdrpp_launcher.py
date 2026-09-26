# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import http.client
import json
import os
import shlex
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from apps.launchers.app_launcher_if import AppLauncherIf, StatusCallback
from apps.launchers.process_manager import close_matching_display_apps, is_process_running, terminate_process
from common.logging.logging_paths import logging_file_path
from protocols.sdrpp_remote_control import SDRPPRemoteControlClient
from config.application_config import SdrSource, SdrSourceConfig

DEFAULT_TERMUX_SDRPP_SOURCE = Path("/root/SDRPlusPlus")
DEFAULT_TERMUX_PROOT_DISTRIBUTION = "debian"
DEFAULT_TERMUX_XDG_RUNTIME_DIR = "/tmp/runtime-root"
DEFAULT_NATIVE_SDRPP_ROOT = Path.home() / "SDRPlusPlus" / "root_dev"
DEFAULT_REMOTE_CONTROL_HOST = "127.0.0.1"
DEFAULT_REMOTE_CONTROL_PORT = 4533
DEFAULT_TERMUX_AUDIO_FIFO = "/tmp/orc-sdrpp-audio.pcm"
DEFAULT_ANDROID_AUDIO_HOST = "127.0.0.1"
DEFAULT_ANDROID_AUDIO_PORT = 8771
DEFAULT_ANDROID_RTL_TCP_CONTROL_HOST = "127.0.0.1"
DEFAULT_ANDROID_RTL_TCP_CONTROL_PORT = 8772
DEFAULT_ANDROID_RTL_TCP_FREQUENCY_HZ = 104_300_000
DEFAULT_ANDROID_RTL_TCP_SAMPLE_RATE = 2_400_000
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

    def __init__(self, *, profile: SDRPPProfile, log_file: str | Path | None = None, fullscreen: bool = True, embedded: bool = False, resource_manager=None, owner_name: str = "sdrpp", rigctl_host: str = "127.0.0.1", rigctl_port: int = 4532, rigctl_timeout_seconds: float = 15.0, remote_control_host: str = DEFAULT_REMOTE_CONTROL_HOST, remote_control_port: int = DEFAULT_REMOTE_CONTROL_PORT, remote_control_timeout_seconds: float = 0.75, termux_proot_distribution: str = DEFAULT_TERMUX_PROOT_DISTRIBUTION, termux_sdrpp_source: str | Path = DEFAULT_TERMUX_SDRPP_SOURCE, theme: str | None = None, sdr_source: SdrSourceConfig | None = None) -> None:
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
        self.sdr_source = sdr_source or SdrSourceConfig()
        self._process: subprocess.Popen[str] | None = None
        self._audio_forwarder_process: subprocess.Popen[str] | None = None
        self._launched_via_proot = False

    def is_running(self) -> bool:
        if self._process is not None:
            if self._process.poll() is None:
                return True
            self._process.wait()
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
            _status(
                set_status,
                f"SDR++ already running; RigCTL unavailable, restarting: {self.profile.name}",
            )
            self.stop(remote_display, set_status)
            time.sleep(0.25)

        if self.theme is not None:
            self.sync_theme()

        if _is_termux():
            self._start_termux_audio()
            self._start_termux_rtl_tcp_provider()

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
        _status(set_status, f"SDR++ launched ({mode}); checking RigCTL...")
        if self.wait_for_rigctl():
            _status(set_status, f"SDR++ ready: {self.profile.name}")
        else:
            _status(set_status, f"SDR++ running; RigCTL unavailable: {self.profile.name}")

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        if self._process is not None:
            terminate_process(self._process)
            self._process = None
        self._stop_termux_audio()
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
        process = self._process
        if process is None or process.poll() is not None:
            raise RuntimeError("SDR++ is not running under this launcher")
        if not self._launched_via_proot:
            return process.pid
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("SDR++ exited while locating its proot child process")
            pid = _find_descendant_matching(process.pid, ("./build/sdrpp", "/build/sdrpp", "SDRPlusPlus"))
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

    def wait_for_rigctl(self) -> bool:
        deadline = time.monotonic() + self.rigctl_timeout_seconds
        last_error: OSError | None = None
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                self._process.wait()
                self._process = None
                raise RuntimeError(f"SDR++ exited before RigCTL became ready. Check log: {self.log_file}")
            try:
                with socket.create_connection((self.rigctl_host, self.rigctl_port), timeout=0.5):
                    return True
            except OSError as exc:
                last_error = exc
                time.sleep(0.5)
        return False

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
        fifo = DEFAULT_TERMUX_AUDIO_FIFO
        shell_command = (
            f"mkdir -p {shlex.quote(runtime_dir)} && chmod 700 {shlex.quote(runtime_dir)} && "
            f"/usr/bin/pulseaudio --daemonize=no --exit-idle-time=-1 "
            f">/tmp/orc-sdrpp-pulseaudio.log 2>&1 & "
            f"pulse_pid=$!; "
            f"pulse_ready=0; "
            f"for attempt in 1 2 3 4 5 6 7 8 9 10; do "
            f"if /usr/bin/pactl info >/dev/null 2>&1; then pulse_ready=1; break; fi; "
            f"if ! kill -0 $pulse_pid 2>/dev/null; then "
            f"cat /tmp/orc-sdrpp-pulseaudio.log >&2; exit 1; fi; "
            f"sleep 0.1; "
            f"done; "
            f"if [ $pulse_ready -ne 1 ]; then "
            f"cat /tmp/orc-sdrpp-pulseaudio.log >&2; exit 1; fi; "
            f"/usr/bin/pactl unload-module module-pipe-sink >/dev/null 2>&1 || true; "
            f"/usr/bin/pactl load-module module-pipe-sink "
            f"sink_name=orc_android file={shlex.quote(fifo)} "
            f"format=s16le rate=48000 channels=2 >/dev/null && "
            f"/usr/bin/pactl set-default-sink orc_android && "
            f"cd {shlex.quote(source)} && exec ./build/sdrpp -r root_dev --autostart"
        )
        return [proot_distro, "login", self.termux_proot_distribution, "--shared-tmp", "--", "env", "-u", "PULSE_SERVER", f"DISPLAY={display}", f"XDG_RUNTIME_DIR={runtime_dir}", "XDG_SESSION_TYPE=x11", "GDK_BACKEND=x11", "LIBGL_ALWAYS_SOFTWARE=1", "bash", "-lc", shell_command]

    def _start_termux_rtl_tcp_provider(self) -> None:
        if self.sdr_source.source is not SdrSource.RTL_TCP:
            return
        if self.sdr_source.host not in ("127.0.0.1", "localhost"):
            return
        if self.sdr_source.port != 1234:
            return

        frequency_hz = self.profile.start_frequency_hz or DEFAULT_ANDROID_RTL_TCP_FREQUENCY_HZ
        body = urllib.parse.urlencode(
            {
                "frequency_hz": frequency_hz,
                "sample_rate": DEFAULT_ANDROID_RTL_TCP_SAMPLE_RATE,
                "port": self.sdr_source.port,
            }
        )
        connection = http.client.HTTPConnection(
            DEFAULT_ANDROID_RTL_TCP_CONTROL_HOST,
            DEFAULT_ANDROID_RTL_TCP_CONTROL_PORT,
            timeout=2.0,
        )
        try:
            connection.request(
                "POST",
                "/rtl-tcp/start",
                body=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = connection.getresponse()
            detail = response.read().decode("utf-8", errors="replace")
            if response.status != 200:
                raise RuntimeError(
                    f"Android Bridge RTL-TCP provider request failed "
                    f"({response.status}): {detail}"
                )
        except OSError as exc:
            raise RuntimeError(
                "Could not reach Android Bridge RTL-TCP control on "
                f"{DEFAULT_ANDROID_RTL_TCP_CONTROL_HOST}:"
                f"{DEFAULT_ANDROID_RTL_TCP_CONTROL_PORT}: {exc}"
            ) from exc
        finally:
            connection.close()

        # The Android driver has no passive readiness endpoint and accepts one
        # effective RTL-TCP client. Never probe port 1234 here because doing so
        # would consume the session intended for SDR++.
        time.sleep(1.0)

    def _start_termux_audio(self) -> None:
        fifo = Path(_termux_shared_tmp_path(Path(DEFAULT_TERMUX_AUDIO_FIFO).name))
        try:
            fifo.unlink(missing_ok=True)
            os.mkfifo(fifo, mode=0o600)
        except OSError as exc:
            raise RuntimeError(f"Could not create SDR++ audio FIFO {fifo}: {exc}") from exc

        forwarder = Path(__file__).with_name("sdrpp_pcm_forwarder.py")
        self._audio_forwarder_process = subprocess.Popen(
            [
                shutil.which("python3") or "python3",
                str(forwarder),
                str(fifo),
                "--host", DEFAULT_ANDROID_AUDIO_HOST,
                "--port", str(DEFAULT_ANDROID_AUDIO_PORT),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            text=True,
        )

    def _stop_termux_audio(self) -> None:
        if self._audio_forwarder_process is not None:
            terminate_process(self._audio_forwarder_process)
            self._audio_forwarder_process = None

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


def _termux_shared_tmp_path(name: str) -> str:
    tmpdir = os.getenv("TMPDIR")
    if not tmpdir:
        raise RuntimeError("Termux TMPDIR is not configured")
    return str(Path(tmpdir) / name)


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
