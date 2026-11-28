# SPDX-License-Identifier: MIT

from concurrent.futures import Future
from unittest.mock import Mock

from controllers.audio.linux_audio_settings import LinuxAudioSettings


def test_bluetooth_monitor_reports_connection_and_stops_scheduling_after_close(monkeypatch):
    dispatcher = Mock()
    dispatcher.dispatch_ui.side_effect = lambda callback: callback()
    controller = LinuxAudioSettings(dispatcher)
    executor = Mock()
    on_status = Mock()
    run = Mock(side_effect=["Device AA:BB:CC:DD:EE:FF Speaker", ""])

    def submit(probe):
        result = Future()
        result.set_result(probe())
        return result

    controller._executor.shutdown(wait=False)
    monkeypatch.setattr(controller, "_executor", executor)
    monkeypatch.setattr(controller, "_run", run)
    executor.submit.side_effect = submit

    controller.monitor_bluetooth(on_status)
    on_status.assert_called_once_with(True)
    run.assert_called_once_with("bluetoothctl", "devices", "Connected")
    dispatcher.schedule_ui_callback.call_args.args[1]()
    assert [call.args for call in on_status.call_args_list] == [(True,), (False,)]

    pending = dispatcher.schedule_ui_callback.call_args.args[1]
    controller.close()
    dispatcher.cancel_ui_callback.assert_called_once_with(
        dispatcher.schedule_ui_callback.return_value
    )
    pending()
    assert executor.submit.call_count == 2
