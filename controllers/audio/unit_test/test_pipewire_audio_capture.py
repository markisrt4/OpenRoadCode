# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.audio.capture.pipewire_audio_capture import PipewireAudioCapture


def test_pipewire_capture_uses_raw_float32_stdout():
    capture = PipewireAudioCapture(sample_rate_hz=48_000, block_size=2048)

    assert capture._build_command() == [
        "pw-record",
        "--raw",
        "--format",
        "f32",
        "--rate",
        "48000",
        "--channels",
        "1",
        "-",
    ]


def test_pipewire_capture_includes_explicit_target():
    capture = PipewireAudioCapture(target="alsa_output.test")

    command = capture._build_command()

    assert command[-3:] == ["--target", "alsa_output.test", "-"]
