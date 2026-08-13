class RpiVirtualKeyboard:
    def show(self) -> None:
        ...

    def hide(self) -> None:
        ...

    @property
    def is_visible(self) -> bool:
        ...
