from .base_input import BaseInput
import dearpygui.dearpygui as dpg


class StringInput(BaseInput):
    """Integer input component."""

    def __init__(self, label: str, default_value: str = "") -> None:
        super().__init__(label, default_value)

    def draw(self) -> None:
        """Draw the string input on the specified parent."""
        dpg.add_input_text(
            label=self.label,
            default_value=self.default_value,
            indent=10,
            tag=self.uuid,
        )
