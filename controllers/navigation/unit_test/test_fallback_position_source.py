# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Host permission never overrides live GPS or resurrects stopped callbacks."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from controllers.navigation.fallback_position_source import FallbackPositionSource
from controllers.navigation.navigation_state import PositionState


def setup_source():
    primary, browser = Mock(), Mock()
    clock = Mock(return_value=0)
    source = FallbackPositionSource(primary, browser, clock=clock)
    consumer = Mock()
    source.start(consumer)
    return source, primary, browser, clock, consumer


def fix(source):
    return PositionState(latitude_deg=42.33, longitude_deg=-83.05, fix_mode=3, source=source)


def test_browser_only_takes_over_missing_or_stale_primary_and_bridge_recovers():
    _, primary, browser, clock, consumer = setup_source()
    bridge_report = primary.start.call_args.args[0]
    browser_report = browser.start.call_args.args[0]
    browser_report(fix('browser'))
    bridge_report(fix('android'))
    clock.return_value = 9
    browser_report(fix('browser'))
    assert [call.args[0].source for call in consumer.call_args_list] == ['browser', 'android']
    clock.return_value = 10
    browser_report(fix('browser'))
    bridge_report(fix('android'))
    browser_report(fix('browser'))
    assert [call.args[0].source for call in consumer.call_args_list] == [
        'browser', 'android', 'browser', 'android',
    ]


@pytest.mark.parametrize('invalid', [
    replace(fix('android'), fix_mode=1),
    replace(fix('android'), is_cached=True),
    replace(fix('android'), latitude_deg=None),
    replace(fix('android'), longitude_deg=float('nan')),
])
def test_unusable_primary_report_does_not_block_browser(invalid):
    _, primary, browser, _, consumer = setup_source()
    primary.start.call_args.args[0](invalid)
    browser.start.call_args.args[0](fix('browser'))
    assert consumer.call_count == 1
    assert consumer.call_args.args[0].source == 'browser'


def test_stop_and_restart_reject_old_reports_and_stop_both_providers():
    source, primary, browser, _, consumer = setup_source()
    old_bridge = primary.start.call_args.args[0]
    old_browser = browser.start.call_args.args[0]
    source.stop()
    primary.stop.assert_called_once()
    browser.stop.assert_called_once()
    old_bridge(fix('android'))
    old_browser(fix('browser'))
    consumer.assert_not_called()
    source.start(consumer)
    old_bridge(fix('android'))
    old_browser(fix('browser'))
    consumer.assert_not_called()
    browser.start.call_args.args[0](fix('browser'))
    assert consumer.call_count == 1


def test_primary_start_failure_keeps_host_source_available():
    primary, browser, consumer = Mock(), Mock(), Mock()
    primary.start.side_effect = OSError('bridge disconnected')
    source = FallbackPositionSource(primary, browser)
    source.start(consumer)
    primary.stop.assert_called_once()
    browser.start.call_args.args[0](fix('browser'))
    assert consumer.call_count == 1
    source.stop()


def test_port_conflict_does_not_disable_primary_gps():
    primary, browser, consumer = Mock(), Mock(), Mock()
    browser.start.side_effect = OSError('address already in use')
    source = FallbackPositionSource(primary, browser)
    source.start(consumer)
    primary.start.call_args.args[0](fix('android'))
    assert consumer.call_count == 1
    source.stop()


def test_both_start_failures_clean_up_and_allow_retry():
    primary, browser = Mock(), Mock()
    primary.start.side_effect = RuntimeError('unavailable')
    browser.start.side_effect = OSError('port busy')
    source = FallbackPositionSource(primary, browser)
    with pytest.raises(RuntimeError, match='Neither primary nor host'):
        source.start(Mock())
    primary.start.side_effect = None
    browser.start.side_effect = None
    consumer = Mock()
    source.start(consumer)
    browser.start.call_args.args[0](fix('browser'))
    assert consumer.call_count == 1
    source.stop()
