# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from hardware_io.audio.pipewire_audio_capture import _pulse_environment


def test_preserves_explicit_pulse_server(monkeypatch) -> None:
    monkeypatch.setenv("PULSE_SERVER","unix:/explicit/pulse/native")

    assert _pulse_environment()["PULSE_SERVER"] == "unix:/explicit/pulse/native"


def test_detects_native_socket_in_xdg_runtime_directory(tmp_path,monkeypatch) -> None:
    pulse_dir=tmp_path/"pulse";pulse_dir.mkdir()
    pulse_socket=pulse_dir/"native"
    pulse_socket.touch()
    monkeypatch.delenv("PULSE_SERVER",raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR",str(tmp_path))
    assert _pulse_environment()["PULSE_SERVER"] == f"unix:{pulse_socket}"
