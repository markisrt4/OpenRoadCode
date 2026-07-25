import tkinter as tk


class VolumeIndicator(tk.Frame):
    """Render a compact segmented volume-level indicator."""
    def __init__(
        self,
        parent: tk.Widget,
        steps: int = 8,
        initial_level: int = 5,
        bg: str = "#dce6ee",
        active: str = "#0d6fd8",
        inactive: str = "#7f8a96",
    ) -> None:
        super().__init__(parent, bg=bg)

        self.steps = max(1, steps)
        self.level = max(0, min(initial_level, self.steps))
        self.active = active
        self.inactive = inactive

        self.bars: list[tk.Frame] = []
        self._build()

    def _build(self) -> None:
        for index in range(self.steps):
            bar = tk.Frame(
                self,
                bg=self.inactive,
                width=5,
                height=8 + index * 2,
            )
            bar.pack(side="left", padx=1, anchor="s")
            self.bars.append(bar)

        self.set_level(self.level)

    def set_level(self, level: int) -> None:
        self.level = max(0, min(level, self.steps))

        for index, bar in enumerate(self.bars):
            bar.configure(
                bg=self.active if index < self.level else self.inactive
            )
