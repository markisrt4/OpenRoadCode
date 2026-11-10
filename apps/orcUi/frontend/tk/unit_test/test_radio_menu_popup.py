# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import unittest
from unittest.mock import Mock
from apps.orcUi.frontend.tk.radio_panel import RadioPanel


class RadioMenuPopupTest(unittest.TestCase):
    def test_bound_popup_positions_menu_and_releases_grab(self):
        panel = object.__new__(RadioPanel)
        menu, button = Mock(), Mock()
        button.winfo_rootx.return_value = 10
        button.winfo_rooty.return_value = 20
        button.winfo_height.return_value = 30
        panel._popup_menu(menu, button)
        menu.tk_popup.assert_called_once_with(10, 50)
        menu.grab_release.assert_called_once_with()
