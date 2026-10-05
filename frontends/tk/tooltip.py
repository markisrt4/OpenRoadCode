# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk tooltip presentation; scheduling policy lives behind UI contracts."""

import tkinter as tk

from ui.tooltip_if import TooltipFactoryIf, TooltipRequestHandlerIf, TooltipState, TooltipUiIf


class TkTooltip(TooltipUiIf):
    """Translate hover/focus events into requests and render a nearby popup."""

    def __init__(self, target: tk.Misc, text: str, factory: TooltipFactoryIf,
                 *, background: str, foreground: str) -> None:
        if not isinstance(factory, TooltipFactoryIf):
            raise TypeError("Tooltip requires TooltipFactoryIf")
        self._target = target
        self._text = text
        self._background = background
        self._foreground = foreground
        self._popup = None
        self._closed = False
        self._handler = factory.create(self)
        if not isinstance(self._handler, TooltipRequestHandlerIf):
            raise TypeError("Tooltip requires TooltipRequestHandlerIf")
        self._bindings = []
        for event in ("<Enter>", "<FocusIn>"):
            self._bindings.append((event, target.bind(event, self._show_requested, add="+")))
        for event in ("<Leave>", "<FocusOut>", "<ButtonPress>", "<Unmap>"):
            self._bindings.append((event, target.bind(event, self._hide_requested, add="+")))
        self._bindings.append(("<Destroy>", target.bind("<Destroy>", self._destroyed, add="+")))

    def _show_requested(self, _event):
        self._handler.request_show(self._text)

    def _hide_requested(self, _event):
        self._handler.request_hide()

    def _destroyed(self, event):
        if event.widget is self._target:
            self.close()

    def set_tooltip_state(self, state: TooltipState) -> None:
        if self._popup is not None:
            try:
                self._popup.destroy()
            except tk.TclError:
                pass
            self._popup = None
        if self._closed or not state.visible or not self._target.winfo_viewable():
            return
        popup = tk.Toplevel(self._target)
        self._popup = popup
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        tk.Label(popup, text=state.text, bg=self._background, fg=self._foreground,
                 relief=tk.SOLID, borderwidth=1, padx=8, pady=5, wraplength=240,
                 justify=tk.LEFT, font=("Sans", 9)).pack()
        popup.update_idletasks()
        width, height = popup.winfo_reqwidth(), popup.winfo_reqheight()
        x = max(0, min(self._target.winfo_rootx() - width - 8,
                       popup.winfo_screenwidth() - width))
        y = max(0, min(self._target.winfo_rooty(), popup.winfo_screenheight() - height))
        popup.geometry(f"+{x}+{y}")
        popup.deiconify()

    def close(self) -> None:
        """Release event bindings, pending display, and popup on the Tk thread."""
        if self._closed:
            return
        self._handler.close()
        self._closed = True
        for event, binding in self._bindings:
            try:
                self._target.unbind(event, binding)
            except tk.TclError:
                pass
        self._bindings.clear()
