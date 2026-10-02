from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest

from apps.launchers.android_bridge_launcher import (
    AndroidBridgeLauncher, AndroidBridgeLauncherError,
)


@patch('apps.launchers.android_bridge_launcher.subprocess.run')
def test_package_and_fallback_are_encoded_in_one_foreground_handoff(run):
    run.return_value = CompletedProcess([], 0, '', '')
    uri = 'https://example.com/order?a=1&name=café'
    assert AndroidBridgeLauncher().open_package_or_uri('com.panera.bread', uri) == 'Android'
    args = run.call_args.args[0]
    assert args[0] == 'termux-open-url'
    link = urlsplit(args[1])
    assert (link.scheme, link.netloc) == ('orcbridge', 'launch')
    assert parse_qs(link.query) == {'package': ['com.panera.bread'], 'uri': [uri]}
    assert run.call_args.kwargs['timeout'] == 5


@patch('apps.launchers.android_bridge_launcher.subprocess.run')
def test_website_handoff_omits_package(run):
    run.return_value = CompletedProcess([], 0, '', '')
    AndroidBridgeLauncher().open_uri('https://example.com')
    assert parse_qs(urlsplit(run.call_args.args[0][1]).query) == {
        'uri': ['https://example.com'],
    }


@pytest.mark.parametrize('failure', [OSError('missing'), TimeoutExpired('termux-open-url', 5)])
@patch('apps.launchers.android_bridge_launcher.subprocess.run')
def test_handoff_execution_errors_are_reported(run, failure):
    run.side_effect = failure
    with pytest.raises(AndroidBridgeLauncherError):
        AndroidBridgeLauncher().open_uri('https://example.com')


@patch('apps.launchers.android_bridge_launcher.subprocess.run')
def test_nonzero_handoff_reports_diagnostic(run):
    run.return_value = CompletedProcess([], 1, '', 'No URL handler')
    with pytest.raises(AndroidBridgeLauncherError, match='No URL handler'):
        AndroidBridgeLauncher().open_uri('https://example.com')


@pytest.mark.parametrize('uri', ['file:///etc/passwd', 'intent://example', 'https:///missing', ''])
@patch('apps.launchers.android_bridge_launcher.subprocess.run')
def test_invalid_fallback_is_rejected_before_handoff(run, uri):
    with pytest.raises(ValueError):
        AndroidBridgeLauncher().open_uri(uri)
    run.assert_not_called()
