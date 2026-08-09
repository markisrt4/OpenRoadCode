"""Toolkit-independent UI contracts and reusable interaction logic."""

from ui.screen_navigator_if import ScreenNavigatorIf
from ui.screen_ui_if import ScreenId, ScreenUiIf
from ui.screen_ui_stub import ScreenUiStub
from ui.ui_action import UiAction
from ui.ui_dispatcher_if import UiDispatcherIf
from ui.ui_event_handler_if import UiEventHandlerIf
from ui.ui_if import UiIf

__all__ = [
    "ScreenId",
    "ScreenNavigatorIf",
    "ScreenUiIf",
    "ScreenUiStub",
    "UiAction",
    "UiDispatcherIf",
    "UiEventHandlerIf",
    "UiIf",
]
