"""Disabled ADS-B lifecycle regression coverage."""

from unittest.mock import Mock

import pytest

from apps.orcUi.adapters.adsb_control import OrcUiAdsbControl


def test_disabled_adsb_blocks_hardware_and_browser(monkeypatch):
    monkeypatch.setenv("ORC_NO_ADSB", "1")
    launcher = Mock()
    managed = Mock()
    control = OrcUiAdsbControl(launcher, set_managed_tracking=managed, managed_tracking=managed)
    assert not control.running
    assert not control.tracking
    assert control.aircraft_count == 0
    assert not control.set_tracking(True)
    assert not control.set_tracking(False)
    with pytest.raises(RuntimeError, match="ADS-B intentionally disabled"):
        control.assert_available()
    with pytest.raises(RuntimeError, match="ADS-B intentionally disabled"):
        control.launch(":99")
    control.stop(":99")
    assert not launcher.mock_calls
    managed.assert_not_called()
