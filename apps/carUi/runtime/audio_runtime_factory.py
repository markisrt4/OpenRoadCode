# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Select system audio control for the active deployment target."""

import logging
import re
import subprocess

from config.runtime_config import AudioConfig
from config.runtime_target import RuntimeTarget, detect_runtime_target
from controllers.audio import (
    AudioControllerIf,
    PactlAudioController,
    PipewireAudioController,
)


LOGGER = logging.getLogger(__name__)


def create_audio_controller(
    *,
    target: RuntimeTarget | None = None,
    steps: int = 20,
    config: AudioConfig = AudioConfig(),
) -> AudioControllerIf:
    """Create the audio controller appropriate for a runtime target.

    @param target Explicit target, or `None` to detect the current host.
    @param steps Number of discrete volume levels.
    @param config Preferred output and optional stable device-name match.
    @return Platform-appropriate system audio controller.
    """
    resolved_target = target or detect_runtime_target()
    output = _resolve_output(config.output, resolved_target)
    if resolved_target is RuntimeTarget.LINUX_DEV:
        sink = (
            PactlAudioController.DEFAULT_SINK
            if output == "default"
            else _resolve_pactl_sink(output, config.device_match)
        )
        return PactlAudioController(steps=steps, sink=sink)
    sink = _resolve_wpctl_sink(output, config.device_match)
    return PipewireAudioController(steps=steps, sink=sink)


def _resolve_output(output: str, target: RuntimeTarget) -> str:
    if output != "auto":
        return output
    if target is RuntimeTarget.RPI4:
        return "onboard-analog"
    if target is RuntimeTarget.RPI5:
        return "usb"
    return "default"


def _resolve_wpctl_sink(output: str, device_match: str | None) -> str:
    if output == "default":
        return PipewireAudioController.DEFAULT_SINK
    try:
        result = subprocess.run(
            ["wpctl", "status", "-n"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        LOGGER.warning("Unable to enumerate PipeWire sinks: %s", exc)
        return PipewireAudioController.DEFAULT_SINK
    sink = _match_wpctl_sink(result.stdout, output, device_match)
    if sink is None:
        LOGGER.warning(
            "Preferred %s PipeWire sink was not found; using default", output
        )
        return PipewireAudioController.DEFAULT_SINK
    return sink


def _match_wpctl_sink(
    status: str,
    output: str,
    device_match: str | None,
) -> str | None:
    patterns = (
        (device_match,)
        if device_match
        else (
            ("usb", "USB Audio")
            if output == "usb"
            else ("bcm2835", "headphones")
        )
    )
    for line in status.splitlines():
        match = re.search(r"(?:\*\s*)?(\d+)\.\s+(.+)", line)
        if match and any(
            pattern and pattern.casefold() in match.group(2).casefold()
            for pattern in patterns
        ):
            return match.group(1)
    return None


def _resolve_pactl_sink(output: str, device_match: str | None) -> str:
    try:
        result = subprocess.run(
            ["pactl", "list", "short", "sinks"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        LOGGER.warning("Unable to enumerate pactl sinks: %s", exc)
        return PactlAudioController.DEFAULT_SINK
    patterns = (
        (device_match,)
        if device_match
        else (("usb",) if output == "usb" else ("analog",))
    )
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) >= 2 and any(
            pattern and pattern.casefold() in line.casefold()
            for pattern in patterns
        ):
            return fields[1]
    LOGGER.warning("Preferred %s pactl sink was not found; using default", output)
    return PactlAudioController.DEFAULT_SINK
