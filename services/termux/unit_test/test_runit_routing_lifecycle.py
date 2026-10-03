# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Routing participates in core startup and reverse-order shutdown."""

from unittest.mock import Mock

from services.termux.service_manager import RunitServiceManager


def test_core_manages_valhalla_before_navigation_and_stops_it_after_navigation():
    manager = RunitServiceManager()
    manager._sv = Mock()
    manager.status = Mock()
    manager.start_core()
    started = [call.args for call in manager._sv.call_args_list]
    assert started == [('up', name) for name in manager.CORE_STACK]
    assert manager.CORE_STACK.index('openroadcode-valhalla') < manager.CORE_STACK.index('openroadcode-navigation')
    manager._sv.reset_mock()
    manager.stop_core()
    assert [call.args for call in manager._sv.call_args_list] == [('down', name) for name in reversed(manager.CORE_STACK)]
