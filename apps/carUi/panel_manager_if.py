from abc import ABC, abstractmethod
import tkinter as tk
from typing import Any


class PanelManagerIf(ABC):
    def __init__(self, app: Any) -> None:
        self.app = app

    @abstractmethod
    def show(self) -> None:
        pass

    def prepare_panel(self, title: str) -> bool:
        if self.app.content_frame is None:
            return False

        self.app.title_label.config(text=title)
        self.app.left_button.config(text="←")
        self.app.left_button.pack(side="left", padx=(10, 0), pady=10)
        self.app._clear_content()

        return True

    def set_status(self, message: str) -> None:
        self.app.status_var.set(message)

    @property
    def content_frame(self) -> tk.Frame:
        return self.app.content_frame

    @property
    def remote_display(self) -> str:
        return self.app.remote_display

    def create_tile(
        self,
        parent: tk.Widget,
        key: str,
        label: str,
        subtitle: str,
        detail: str,
    ) -> tk.Frame:
        return self.app.create_subpanel_tile(parent, key, label, subtitle, detail)
