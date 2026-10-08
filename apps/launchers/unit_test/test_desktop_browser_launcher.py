# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Desktop browser handoffs use argument lists and report actionable failures."""
import subprocess
from unittest.mock import patch

import pytest

from apps.launchers.desktop_browser_launcher import DesktopBrowserLauncher, DesktopBrowserLauncherError


@pytest.mark.parametrize("gio,command", [
    (True, ["/usr/bin/gio", "open", "https://example.com/order?a=1&b=2"]),
    (False, ["/usr/bin/xdg-open", "https://example.com/order?a=1&b=2"]),
])
def test_desktop_opener_preserves_url_and_has_timeout(gio, command):
    with patch("apps.launchers.desktop_browser_launcher.shutil.which",
               side_effect=lambda name: f"/usr/bin/{name}" if name != "gio" or gio else None), patch(
                   "apps.launchers.desktop_browser_launcher.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        DesktopBrowserLauncher().open_uri(command[-1])
        run.assert_called_once_with(command, capture_output=True, text=True, check=False, timeout=5)


@pytest.mark.parametrize("uri", ["javascript:alert(1)", "file:///etc/passwd", "https://user:pass@example.com", "--help"])
def test_invalid_web_target_never_starts_a_process(uri):
    with patch("apps.launchers.desktop_browser_launcher.subprocess.run") as run:
        with pytest.raises(ValueError):
            DesktopBrowserLauncher().open_uri(uri)
        run.assert_not_called()


def test_failed_desktop_handoff_is_reported():
    with patch("apps.launchers.desktop_browser_launcher.shutil.which", return_value="/usr/bin/gio"), patch(
            "apps.launchers.desktop_browser_launcher.subprocess.run",
            return_value=subprocess.CompletedProcess([], 1, "", "No application registered")):
        with pytest.raises(DesktopBrowserLauncherError, match="No application registered"):
            DesktopBrowserLauncher().open_uri("https://example.com")


def test_timed_out_handoff_is_reported_without_automatic_retry():
    with patch("apps.launchers.desktop_browser_launcher.shutil.which", return_value="/usr/bin/gio"), patch(
            "apps.launchers.desktop_browser_launcher.subprocess.run",
            side_effect=subprocess.TimeoutExpired("gio", 5)) as run:
        with pytest.raises(DesktopBrowserLauncherError, match="check whether the browser opened"):
            DesktopBrowserLauncher().open_uri("https://example.com")
        assert run.call_count == 1
