# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from config.runtime_environment import android_bridge_url


def test_android_bridge_url_prefers_process_environment(tmp_path) -> None:
    runtime_file = tmp_path / "runtime.env"
    runtime_file.write_text(
        'OPENROADCODE_ANDROID_BRIDGE_URL="http://192.168.1.20:8766"\n',
        encoding="utf-8",
    )

    assert android_bridge_url(
        "http://127.0.0.1:8766",
        environment={"OPENROADCODE_ANDROID_BRIDGE_URL": "http://192.168.1.30:8766"},
        runtime_environment_file=runtime_file,
    ) == "http://192.168.1.30:8766"


def test_android_bridge_url_reads_shared_runtime_state(tmp_path) -> None:
    runtime_file = tmp_path / "runtime.env"
    runtime_file.write_text(
        'OPENROADCODE_ANDROID_BRIDGE_URL="http://192.168.1.20:8766"\n',
        encoding="utf-8",
    )

    assert android_bridge_url(
        "http://127.0.0.1:8766",
        environment={},
        runtime_environment_file=runtime_file,
    ) == "http://192.168.1.20:8766"


def test_android_bridge_url_falls_back_to_config(tmp_path) -> None:
    assert android_bridge_url(
        "http://127.0.0.1:8766",
        environment={},
        runtime_environment_file=tmp_path / "missing.env",
    ) == "http://127.0.0.1:8766"
