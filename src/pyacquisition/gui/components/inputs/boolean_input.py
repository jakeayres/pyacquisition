from .base_input import BaseInput
import dearpygui.dearpygui as dpg


class BooleanInput(BaseInput):
    """Boolean input component."""

    def __init__(self, label: str, default_value: bool = False) -> None:
        super().__init__(label, default_value)

    def draw(self, parent: str | None = None, width: int = -1) -> None:
        """Draw the boolean input on the specified parent."""
        options = self._options(parent, width)
        del options["width"]  # a checkbox is as wide as its box
        return dpg.add_checkbox(**options)
