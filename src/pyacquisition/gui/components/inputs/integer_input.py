from .base_input import BaseInput
import dearpygui.dearpygui as dpg


class IntegerInput(BaseInput):
    """Integer input component."""

    def __init__(self, label: str, default_value: int = 0) -> None:
        super().__init__(label, default_value)

    def draw(self) -> None:
        """Draw the integer input on the specified parent."""
        dpg.add_input_int(
            label=self.label,
            default_value=self.default_value,
            indent=10,
            tag=self.uuid,
        )
