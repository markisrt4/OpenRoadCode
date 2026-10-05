# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compose tooltip policy against injected UI presentation contracts."""

from controllers.input.tooltip_controller import TooltipController
from ui.tooltip_if import TooltipFactoryIf, TooltipRequestHandlerIf, TooltipUiIf
from ui.ui_dispatcher_if import UiDispatcherIf


class TooltipFactory(TooltipFactoryIf):
    """Create controller sessions using the application's dispatcher."""

    def __init__(self, dispatcher: UiDispatcherIf) -> None:
        self._dispatcher = dispatcher

    def create(self, view: TooltipUiIf) -> TooltipRequestHandlerIf:
        return TooltipController(view, self._dispatcher)
