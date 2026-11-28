# SPDX-License-Identifier: MIT
"""Verify installer boot checks without a systemd daemon."""

from argparse import Namespace
from io import BytesIO
from unittest.mock import Mock
from urllib.error import HTTPError

from scripts.installers import verify_runtime


def test_radio_and_managed_adsb_verify_boot_without_starting_on_demand_units(monkeypatch):
    args = Namespace(
        telemetry_services=False,
        navigation_service=False,
        radio_service=True,
        valhalla_service=False,
        navigation_data_root=None,
        gpsd_service=False,
        service_manager=True,
        vnc_service=False,
        managed_rf=True,
    )
    calls = []

    def state(query, unit, *, user=False):
        calls.append((query, unit, user))
        if unit == "libsdrforge.service" and query == "is-enabled":
            return "enabled-runtime"
        if unit in {"libsdrforge-weather.service", "openroadcode-readsb@.service"}:
            return "static"
        if unit == "readsb.service":
            return "masked"
        return "enabled" if query == "is-enabled" else "active"

    monkeypatch.setattr(verify_runtime, "systemd_state", state)
    monkeypatch.setattr(verify_runtime, "command_output", lambda *command: "yes")
    monkeypatch.setattr(verify_runtime, "report", lambda *args: None)
    assert verify_runtime.verify_boot_services(args, {"adsb"}) == 1
    assert ("is-enabled", "openroadcode-message-broker.service", False) in calls
    assert ("is-enabled", "openroadcode-service-manager.service", False) in calls
    assert ("is-active", "openroadcode-service-manager.service", False) in calls
    assert ("is-active", "lighttpd.service", False) in calls
    assert ("is-enabled", "openroadcode-readsb@.service", True) in calls
    assert ("is-active", "libsdrforge-weather.service", True) not in calls


def test_pairing_verification_uses_unauthenticated_loopback_probe(monkeypatch):
    url = "http://127.0.0.1:8769/services"
    opener = Mock()
    opener.open.side_effect = HTTPError(url, 401, "Unauthorized", {}, BytesIO())
    build_opener = Mock(return_value=opener)
    monkeypatch.setattr(verify_runtime.urllib.request, "build_opener", build_opener)
    monkeypatch.setattr(
        verify_runtime, "command_output", lambda *_: "127.0.0.1 192.168.8.2 fd00::1"
    )

    assert verify_runtime.service_manager_ready() == (True, f"{url}: HTTP 401")
    opener.open.assert_called_once_with(url, timeout=1)
    assert build_opener.call_args.args[0].proxies == {}
    assert verify_runtime.service_manager_pairing_urls() == ["http://192.168.8.2:8769"]
