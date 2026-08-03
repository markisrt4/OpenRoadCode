"""Reusable no-op implementation of the common UI lifecycle."""

from ui.ui_if import UiIf


class UiStub(UiIf):
    """Provide a successful, idempotent no-op UI lifecycle."""

    def initialize(self) -> bool:
        return self._create_window()

    def shutdown(self) -> bool:
        return self._destroy_window()

    def _create_window(self) -> bool:
        return True

    def _destroy_window(self) -> bool:
        return True
