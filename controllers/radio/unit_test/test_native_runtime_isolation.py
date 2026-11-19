# SPDX-License-Identifier: MIT
"""Static and contract guards for SDR++-free native runtime composition."""
import ast
from pathlib import Path

import pytest

from apps.orcUi.native_radio_application_service import NativeRadioApplicationService


def test_native_runtime_has_no_eager_sdrpp_launcher_import():
    source = Path(__file__).resolve().parents[3] / "apps/orcUi/application_runtime.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    assert not [
        node for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module in (
            "apps.launchers.managed_sdrpp_launcher",
            "apps.launchers.sdrpp_launcher",
        )
    ]


def test_native_radio_service_does_not_launch_external_window():
    service = NativeRadioApplicationService()
    service.present()
    assert service.presented is False
    assert service.fullscreen is False
    service.relinquish_for_adsb()
    service.close()
    with pytest.raises(RuntimeError, match="no external window"):
        service.window_process_id(timeout_seconds=1)
