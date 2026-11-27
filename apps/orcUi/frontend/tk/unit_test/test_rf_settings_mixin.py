# SPDX-License-Identifier: MIT
"""Test RF settings completion handling without a Tk display."""

from unittest.mock import Mock

from apps.orcUi.frontend.tk.rf_settings_mixin import RfSettingsMixin


def test_receiver_settings_ignore_stale_and_destroyed_view_results():
    view = RfSettingsMixin()
    view._rf_hardware_config = Mock()
    view._rf_hardware_status = Mock()
    view._rf_gain = Mock()
    view._rf_ppm = Mock()
    view._rf_agc = Mock()
    config = {
        "sample_rate_hz": 2400000,
        "gain_db": 29.7,
        "ppm_correction": -2,
        "rtl_agc_enabled": True,
    }

    view._load_rf_hardware()
    first_result, _ = view._rf_hardware_config.load.call_args.args
    view._load_rf_hardware()
    current_result, _ = view._rf_hardware_config.load.call_args.args
    first_result(config)
    view._rf_gain.set.assert_not_called()

    current_result(config)
    view._rf_gain.set.assert_called_once_with("29.7")
    view._rf_hardware_status.winfo_exists.return_value = False
    view._rf_gain.reset_mock()
    current_result(config)
    view._rf_gain.set.assert_not_called()
