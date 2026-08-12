# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for the shared Tk screen lifecycle."""

import unittest

from apps.carUi.screens.car_ui_screen import CarUiScreen
from ui.screen_ui_if import ScreenId, ScreenUiIf
from ui.ui_action import UiAction


class FakeTopBar:
    def __init__(self) -> None:
        self.title: str | None = None
        self.back_button_visible = False

    def set_title(self, title: str) -> None:
        self.title = title

    def show_back_button(self) -> None:
        self.back_button_visible = True


class FakeApp:
    def __init__(self) -> None:
        self.active_screen: ScreenUiIf | None = None
        self.clear_count = 0
        self.top_bar = FakeTopBar()

    def activate_screen(self, screen: ScreenUiIf) -> None:
        self.active_screen = screen

    def clear_screen_content(self) -> None:
        self.clear_count += 1

    def set_screen_title(self, title: str) -> None:
        self.top_bar.set_title(title)

    def set_screen_status(self, _message: str) -> None:
        pass

    def set_screen_back_action(self, _action) -> None:
        self.top_bar.show_back_button()

    @property
    def screen_parent(self):
        return None


class ExampleScreen(CarUiScreen):
    def __init__(self, app: FakeApp) -> None:
        super().__init__(
            app,  # type: ignore[arg-type]
            ScreenId("example"),
            create_menu_tile=lambda *_args: None,  # type: ignore[arg-type]
        )

    def show(self) -> None:
        self.prepare_screen("Example", lambda: None)


class CarUiScreenTest(unittest.TestCase):
    def test_show_activates_and_prepares_screen(self) -> None:
        app = FakeApp()
        screen = ExampleScreen(app)

        screen.show()

        self.assertIs(app.active_screen, screen)
        self.assertEqual(app.clear_count, 1)
        self.assertEqual(app.top_bar.title, "Example")
        self.assertTrue(app.top_bar.back_button_visible)
        self.assertEqual(screen.screen_id, ScreenId("example"))

    def test_actions_are_unhandled_by_default(self) -> None:
        screen = ExampleScreen(FakeApp())

        self.assertFalse(screen.handle_ui_action(UiAction.SELECT))


if __name__ == "__main__":
    unittest.main()
