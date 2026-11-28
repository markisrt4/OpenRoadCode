# SPDX-License-Identifier: MIT

from unittest.mock import Mock

from apps.orcUi.frontend.tk.bluetooth_button import BluetoothButton


def test_bluetooth_shortcut_sets_command_and_uses_same_color_for_icon_and_label(monkeypatch):
    image = Mock()
    monkeypatch.setattr(
        "apps.orcUi.frontend.tk.bluetooth_button.tk.PhotoImage", Mock(return_value=image)
    )
    button = BluetoothButton.__new__(BluetoothButton)
    button._color = ""
    button.configure = Mock()
    action = Mock()

    button.set_action(action)
    assert button.configure.call_args.kwargs["command"] is action

    for color in ("#60a5fa", "#9ca3af"):
        button.set_color(color)
        assert button.configure.call_args.kwargs["fg"] == color
        assert button.configure.call_args.kwargs["activeforeground"] == color
        assert button.configure.call_args.kwargs["image"] is image
        assert all(call.args[0] == color for call in image.put.call_args_list)
        image.put.reset_mock()
