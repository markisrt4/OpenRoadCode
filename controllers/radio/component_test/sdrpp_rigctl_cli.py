"""Command-line component test for SDR++ and the rigctl backend."""

from __future__ import annotations

import argparse
import shlex
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Optional, Sequence

from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend
from protocols.rigctl import RigctlClient


@dataclass(frozen=True)
class TestConfiguration:
    host: str
    port: int
    frequency_hz: Optional[int]
    mode: Optional[str]
    bandwidth: Optional[int]
    launch_command: Optional[str]
    startup_timeout_seconds: float


def parse_args(argv: Optional[Sequence[str]] = None) -> TestConfiguration:
    parser = argparse.ArgumentParser(
        description="Exercise a running SDR++ rigctl server through RigctlRadioBackend."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4532)
    parser.add_argument("--frequency", type=int, dest="frequency_hz")
    parser.add_argument("--mode")
    parser.add_argument("--bandwidth", type=int)
    parser.add_argument(
        "--launch-command",
        help='Optional command used to launch SDR++, for example: "sdrpp"',
    )
    parser.add_argument("--startup-timeout", type=float, default=15.0)
    args = parser.parse_args(argv)

    if args.frequency_hz is not None and args.frequency_hz <= 0:
        parser.error("--frequency must be greater than zero")
    if args.bandwidth is not None and args.bandwidth < 0:
        parser.error("--bandwidth must not be negative")
    if (args.mode is None) != (args.bandwidth is None):
        parser.error("--mode and --bandwidth must be supplied together")

    return TestConfiguration(
        host=args.host,
        port=args.port,
        frequency_hz=args.frequency_hz,
        mode=args.mode,
        bandwidth=args.bandwidth,
        launch_command=args.launch_command,
        startup_timeout_seconds=args.startup_timeout,
    )


def port_is_open(host: str, port: int, timeout_seconds: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def wait_for_port(host: str, port: int, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if port_is_open(host, port):
            return
        time.sleep(0.25)
    raise TimeoutError(
        f"rigctl server did not become available at {host}:{port} "
        f"within {timeout_seconds:.1f} seconds"
    )


def create_client(host: str, port: int) -> RigctlClient:
    try:
        return RigctlClient(host=host, port=port)
    except TypeError:
        return RigctlClient(host, port)


def main(argv: Optional[Sequence[str]] = None) -> None:
    config = parse_args(argv)
    process: Optional[subprocess.Popen[bytes]] = None
    launched_process = False

    print("SDR++ rigctl component test\n")

    try:
        if not port_is_open(config.host, config.port):
            if config.launch_command is None:
                raise ConnectionError(
                    f"no rigctl server is listening at {config.host}:{config.port}; "
                    "start SDR++ or provide --launch-command"
                )

            command = shlex.split(config.launch_command)
            if not command:
                raise ValueError("--launch-command must not be empty")

            print(f"[INFO] Launching: {config.launch_command}")
            process = subprocess.Popen(command,
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL,)
            launched_process = True
            wait_for_port(
                config.host,
                config.port,
                config.startup_timeout_seconds,
            )
            print(f"[PASS] rigctl server available at {config.host}:{config.port}")
        else:
            print(f"[PASS] rigctl server available at {config.host}:{config.port}")

        backend = RigctlRadioBackend(create_client(config.host, config.port))
        original_frequency = backend.get_frequency()
        print(f"[PASS] Read current frequency: {original_frequency} Hz")

        try:
            if config.frequency_hz is not None:
                backend.set_frequency(config.frequency_hz)
                actual_frequency = backend.get_frequency()
                if actual_frequency != config.frequency_hz:
                    raise AssertionError(
                        f"frequency readback mismatch: requested "
                        f"{config.frequency_hz}, received {actual_frequency}"
                    )
                print(f"[PASS] Set and verified frequency: {actual_frequency} Hz")

            if config.mode is not None and config.bandwidth is not None:
                backend.set_mode(config.mode, config.bandwidth)
                print(
                    f"[PASS] Set mode: {config.mode}, "
                    f"bandwidth: {config.bandwidth} Hz"
                )

            signal_strength = backend.get_signal_strength()
            print(f"[INFO] Signal strength: {signal_strength or 'unavailable'}")

            snr = backend.get_snr()
            print(f"[INFO] SNR: {snr or 'unavailable'}")

            rds = backend.get_rds()
            print(f"[INFO] RDS: {rds or 'unavailable'}")
        finally:
            if config.frequency_hz is not None:
                backend.set_frequency(original_frequency)
                restored_frequency = backend.get_frequency()
                if restored_frequency != original_frequency:
                    raise AssertionError(
                        f"failed to restore frequency: expected "
                        f"{original_frequency}, received {restored_frequency}"
                    )
                print(f"[PASS] Restored original frequency: {original_frequency} Hz")

        print("\nSDR++ rigctl component test: PASS")
    finally:
        if launched_process and process is not None:
            process.terminate()
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)
            print("[INFO] Stopped launched SDR++ process")


if __name__ == "__main__":
    main()
