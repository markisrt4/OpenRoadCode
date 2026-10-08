# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify toolkit events and popup cleanup through tooltip contracts."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from frontends.tk.tooltip import TkTooltip
from ui.tooltip_if import TooltipFactoryIf, TooltipRequestHandlerIf, TooltipState


def test_hover_focus_click_unmap_and_destroy_use_request_contract():
    target = Mock()
    factory = Mock(spec=TooltipFactoryIf)
    factory.create.return_value = Mock(spec=TooltipRequestHandlerIf)
    bindings = {}
    target.bind.side_effect = lambda event, callback, **_kw: bindings.setdefault(event, callback)
    tooltip = TkTooltip(target, "Zoom in", factory, background="black", foreground="white")
    handler = factory.create.return_value
    bindings["<Enter>"](None)
    bindings["<FocusIn>"](None)
    assert handler.request_show.call_count == 2
    handler.request_show.assert_called_with("Zoom in")
    for event in ("<Leave>", "<FocusOut>", "<ButtonPress>", "<Unmap>"):
        bindings[event](None)
    assert handler.request_hide.call_count == 4
    bindings["<Destroy>"](SimpleNamespace(widget=object()))
    handler.close.assert_not_called()
    bindings["<Destroy>"](SimpleNamespace(widget=target))
    tooltip.close()
    handler.close.assert_called_once()
    assert target.unbind.call_count == 7


@patch("frontends.tk.tooltip.tk.Label")
@patch("frontends.tk.tooltip.tk.Toplevel")
def test_popup_placement_is_clamped_and_hidden_state_releases_window(toplevel, _label):
    target = Mock()
    target.winfo_rootx.return_value = 10
    target.winfo_rooty.return_value = 900
    popup = toplevel.return_value
    popup.winfo_reqwidth.return_value = 200
    popup.winfo_reqheight.return_value = 40
    popup.winfo_screenwidth.return_value = 800
    popup.winfo_screenheight.return_value = 600
    factory = Mock(spec=TooltipFactoryIf)
    factory.create.return_value = Mock(spec=TooltipRequestHandlerIf)
    tooltip = TkTooltip(target, "Recenter", factory,
                        background="black", foreground="white")
    tooltip.set_tooltip_state(TooltipState("Recenter", True))
    popup.geometry.assert_called_once_with("+0+560")
    popup.deiconify.assert_called_once()
    tooltip.set_tooltip_state(TooltipState())
    popup.destroy.assert_called_once()
    tooltip.close()
    tooltip.set_tooltip_state(TooltipState("obsolete", True))
    toplevel.assert_called_once()
