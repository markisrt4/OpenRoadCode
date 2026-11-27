# SPDX-License-Identifier: MIT
"""Verify that inventory reports observed unit states."""

from scripts.installers import installation_inventory


def test_user_units_show_live_state_and_missing_units(monkeypatch, capsys):
    def output(*args):
        assert args[:3] == ("systemctl", "--user", "show")
        if args[-1] == "libsdrforge.service":
            return "LoadState=loaded\nUnitFileState=disabled\nActiveState=active"
        return "LoadState=not-found\nActiveState=inactive"

    monkeypatch.setattr(installation_inventory, "command_output", output)
    installation_inventory.show_units(("libsdrforge.service", "absent.service"), user=True)
    assert capsys.readouterr().out == (
        "libsdrforge.service\n  loaded | boot: disabled | now: active\nabsent.service\n  Missing\n"
    )
