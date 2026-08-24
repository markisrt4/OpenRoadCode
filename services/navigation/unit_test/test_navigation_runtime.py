# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for navigation runtime ownership and telemetry publication."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from services.navigation.navigation_runtime import NavigationRuntime


def test_runtime_rejects_nonpositive_rate():
    with pytest.raises(ValueError):
        NavigationRuntime(Mock(), Mock(), source="test", rate_hz=0.0)


def test_runtime_uses_supplied_controller_for_command_service():
    controller = Mock()
    publisher = Mock()
    runtime = NavigationRuntime(
        controller,
        publisher,
        source="test-navigation",
        command_endpoint="inproc://navigation-runtime-unit-test",
    )
    try:
        # The command service is deliberately constructed from the same controller
        # instance used by the telemetry loop. This is the ownership invariant the
        # runtime exists to enforce.
        assert runtime._command_server._service._controller is controller
    finally:
        runtime.close()
