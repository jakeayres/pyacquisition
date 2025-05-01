from .base_input import BaseInput
import dearpygui.dearpygui as dpg


class FloatInput(BaseInput):
    """Float input component."""
    
    def __init__(self, label: str, default_value: float = 0.0) -> None:
        super().__init__(label, default_value)

    def draw(self) -> None:
        """Draw the float input on the specified parent."""
        dpg.add_input_float(
            label=self.label,
            default_value=self.default_value,
            indent=10,
            tag=self.uuid,
        )