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
