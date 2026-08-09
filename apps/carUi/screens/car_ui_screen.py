"""Car UI-specific helpers shared by its Tk screens."""

import tkinter as tk
from collections.abc import Callable

from apps.carUi.screens.car_ui_screen_services import MenuTileFactory
from frontends.tk import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId


class CarUiScreen(TkScreen):
    """Adapt reusable Tk screen lifecycle to the current Car UI shell."""

    def __init__(
        self,
        host: TkScreenHostIf,
        screen_id: ScreenId,
        create_menu_tile: MenuTileFactory,
    ) -> None:
        super().__init__(screen_id)
        self.host = host
        self._create_menu_tile = create_menu_tile

    def prepare_screen(
        self,
        title: str,
        back_action: Callable[[], None],
    ) -> bool:
        self.host.activate_screen(self)
        self.host.clear_screen_content()
        self.host.set_screen_title(title)
        self.host.set_screen_back_action(back_action)
        return True

    def set_title(self, title: str) -> None:
        self.host.set_screen_title(title)

    def set_status(self, message: str) -> None:
        self.host.set_screen_status(message)

    @property
    def content_frame(self) -> tk.Frame:
        return self.host.screen_parent

    def create_tile(
        self,
        parent: tk.Widget,
        key: str,
        label: str,
        subtitle: str,
        detail: str,
    ) -> tk.Frame:
        return self._create_menu_tile(parent, key, label, subtitle, detail)
