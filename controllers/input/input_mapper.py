# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Default mapping from generic input events to UI actions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
)
from controllers.input.input_mapper_if import InputMapperIf
from ui.ui_action import UiAction


class InputMapper(InputMapperIf):
    """Default input mapping."""

    def __init__(
        self,
        user_encoder_id: InputDeviceId | Iterable[InputDeviceId],
        volume_encoder_id: InputDeviceId,
        push_button_actions: Mapping[InputDeviceId, UiAction] | None = None,
    ) -> None:
        if isinstance(user_encoder_id, InputDeviceId):
            self._user_encoder_ids = frozenset((user_encoder_id,))
        else:
            self._user_encoder_ids = frozenset(user_encoder_id)
        self._volume_encoder_id = volume_encoder_id
        self._push_button_actions = dict(push_button_actions or {})

    def map_input(
        self,
        event: InputEvent,
    ) -> UiAction | None:
        """Map one physical input event into a semantic UI action."""

        if event.device_id in self._user_encoder_ids:
            return self._map_user_encoder(event)

        if event.device_id == self._volume_encoder_id:
            return self._map_volume_encoder(event)

        if event.device_id.device_type is InputDeviceType.KEYBOARD:
            return self._map_keyboard(event)

        if event.device_id.device_type is InputDeviceType.PUSHBUTTON:
            if event.event_type is InputEventType.BUTTON_PRESSED:
                return self._push_button_actions.get(event.device_id)
            return None

        return None

    def _map_user_encoder(
        self,
        event: InputEvent,
    ) -> UiAction | None:
        if event.event_type is InputEventType.ROTATED:
            turns = self._get_rotation_value(event)

            if turns > 0:
                return UiAction.NAVIGATE_DOWN

            if turns < 0:
                return UiAction.NAVIGATE_UP

        if event.event_type is InputEventType.BUTTON_PRESSED:
            return UiAction.SELECT

        return None

    def _map_volume_encoder(
        self,
        event: InputEvent,
    ) -> UiAction | None:
        if event.event_type is InputEventType.BUTTON_PRESSED:
            return UiAction.VOLUME_MUTE

        if event.event_type is not InputEventType.ROTATED:
            return None

        turns = self._get_rotation_value(event)

        if turns > 0:
            return UiAction.VOLUME_UP

        if turns < 0:
            return UiAction.VOLUME_DOWN

        return None

    def _map_keyboard(
        self,
        event: InputEvent,
    ) -> UiAction | None:
        if event.event_type is not InputEventType.BUTTON_PRESSED:
            return None

        if not isinstance(event.value, str):
            return None

        key_mapping = {
            "KEY_UP": UiAction.NAVIGATE_UP,
            "KEY_DOWN": UiAction.NAVIGATE_DOWN,
            "KEY_LEFT": UiAction.NAVIGATE_UP,
            "KEY_RIGHT": UiAction.NAVIGATE_DOWN,
            "KEY_ENTER": UiAction.SELECT,
            "KEY_KPENTER": UiAction.SELECT,
            "KEY_SPACE": UiAction.SELECT,
            "KEY_ESC": UiAction.BACK,
            "KEY_BACKSPACE": UiAction.BACK,
            "KEY_HOME": UiAction.HOME,
            "KEY_VOLUMEUP": UiAction.VOLUME_UP,
            "KEY_VOLUMEDOWN": UiAction.VOLUME_DOWN,
        }

        return key_mapping.get(event.value.upper())

    @staticmethod
    def _get_rotation_value(event: InputEvent) -> int:
        if not isinstance(event.value, int):
            return 0

        return event.value
