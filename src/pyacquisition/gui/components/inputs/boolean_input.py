from .base_input import BaseInput
import dearpygui.dearpygui as dpg


class BooleanInput(BaseInput):
    """Boolean input component."""
    

    def __init__(self, label: str, default_value: bool = False) -> None:
        super().__init__(label, default_value)


    def draw(self) -> None:
        """Draw the boolean input on the specified parent."""
        dpg.add_checkbox(
            label=self.label,
            default_value=self.default_value,
            indent=10,
            tag=self.uuid,
        )