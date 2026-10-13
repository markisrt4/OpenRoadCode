# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import tkinter as tk
import unittest
from unittest.mock import Mock

from apps.orcUi.frontend.tk.gradient_control import GradientControl


class GradientControlTest(unittest.TestCase):
    def control(self):
        control = object.__new__(GradientControl)
        control._command = Mock()
        control._state = tk.NORMAL
        control.winfo_width = lambda: 100
        control.winfo_height = lambda: 44
        return control

    def test_disabled_control_does_not_activate(self):
        control = self.control()
        control._state = tk.DISABLED
        control.invoke()
        control._command.assert_not_called()

    def test_release_outside_does_not_activate(self):
        control = self.control()
        control._release(Mock(x=110, y=20))
        control._command.assert_not_called()
        control._release(Mock(x=50, y=20))
        control._command.assert_called_once_with()


    def test_redraw_during_tcl_owned_dialog_focus_and_restore(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Requires an X11/Tk display")
        try:
            errors = []
            root.report_callback_exception = lambda *args: errors.append(args)
            control = GradientControl(root, command=Mock(), bg="#102030", fg="white",
                                      activebackground="#2080b0", activeforeground="white",
                                      font=("Sans", 9), text="Performance")
            control.pack()
            root.update()
            # Reproduce the color picker's Tcl-owned focus without opening a
            # blocking modal dialog. These widgets have no Python wrappers.
            root.tk.call("toplevel", ".__tk__color")
            root.tk.call("entry", ".__tk__color.entry")
            root.tk.call("pack", ".__tk__color.entry")
            root.update()
            root.tk.call("focus", "-force", ".__tk__color.entry")
            root.update()
            with self.assertRaises(KeyError):
                control.focus_get()
            control.configure(text="CPU 10%", fg="#80d080")
            root.update()
            outlines = [item for item in control.find_all()
                        if control.type(item) == "rectangle" and control.itemcget(item, "outline")]
            self.assertEqual(outlines, [])
            root.tk.call("destroy", ".__tk__color")
            control.focus_force()
            root.update()
            control.configure(text="CPU 12%")
            outlines = [item for item in control.find_all()
                        if control.type(item) == "rectangle" and control.itemcget(item, "outline")]
            self.assertEqual(len(outlines), 1)
            self.assertEqual(errors, [])
        finally:
            root.destroy()
