# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Diagnostic status must distinguish installation from a running Android runtime."""
from unittest.mock import Mock

from scripts import probe_android_navigation as probe


def test_missing_waydroid_does_not_run_commands(monkeypatch):
    monkeypatch.setattr(probe.shutil, 'which', lambda _name: None)
    query = Mock()
    monkeypatch.setattr(probe, 'query', query)
    assert probe.waydroid_facts()['installed'] is False
    query.assert_not_called()


def test_success_exit_with_stopped_session_is_not_runtime_readiness(monkeypatch):
    monkeypatch.setattr(probe.shutil, 'which', lambda _name: '/usr/bin/waydroid')
    query = Mock(return_value=(0, 'Session: STOPPED\nContainer: RUNNING\nIP address: private\n'))
    monkeypatch.setattr(probe, 'query', query)
    facts = probe.waydroid_facts()
    assert facts['session'] == 'STOPPED'
    assert facts['waze_package'] == 'not checked'
    assert 'private' not in str(facts)
    query.assert_called_once_with(['waydroid', 'status'])


def test_running_runtime_checks_only_waze_package_without_app_inventory(monkeypatch):
    monkeypatch.setattr(probe.shutil, 'which', lambda _name: '/usr/bin/waydroid')
    query = Mock(side_effect=[(0, 'Session: RUNNING\nContainer: RUNNING\n'),
        (0, 'Name: Waze\npackageName: com.waze\nName: Other\npackageName: private.app\n')])
    monkeypatch.setattr(probe, 'query', query)
    facts = probe.waydroid_facts()
    assert facts['waze_package'] is True
    assert 'private.app' not in str(facts)
    assert query.call_args.args[0] == ['waydroid', 'app', 'list']


def test_failed_status_is_unknown_not_stopped_or_missing(monkeypatch):
    monkeypatch.setattr(probe.shutil, 'which', lambda _name: '/usr/bin/waydroid')
    monkeypatch.setattr(probe, 'query', Mock(return_value=(None, '')))
    assert probe.waydroid_facts() == {'installed': True, 'runtime': 'query failed or unavailable'}
