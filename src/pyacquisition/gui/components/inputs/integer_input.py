from .base_input import BaseInput
import dearpygui.dearpygui as dpg


class IntegerInput(BaseInput):
    """Integer input component."""

    def __init__(self, label: str, default_value: int = 0) -> None:
        super().__init__(label, default_value)

    def draw(self, parent: str | None = None, width: int = -1) -> None:
        """Draw the integer input on the specified parent."""
        return dpg.add_input_int(**self._options(parent, width), step=0)
