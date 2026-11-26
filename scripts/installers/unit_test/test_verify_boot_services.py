# SPDX-License-Identifier: MIT
"""Verify installer boot checks without a systemd daemon."""

from argparse import Namespace

from scripts.installers import verify_runtime


def test_radio_and_managed_adsb_verify_boot_without_starting_on_demand_units(monkeypatch):
    args = Namespace(
        telemetry_services=False,
        navigation_service=False,
        radio_service=True,
        valhalla_service=False,
        navigation_data_root=None,
        gpsd_service=False,
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
    assert ("is-active", "lighttpd.service", False) in calls
    assert ("is-enabled", "openroadcode-readsb@.service", True) in calls
    assert ("is-active", "libsdrforge-weather.service", True) not in calls
