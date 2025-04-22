import dearpygui.dearpygui as dpg


class BaseInput:
    """Base class for input components."""
    
    def __init__(self, label: str, default_value=None) -> None:
        self.label = label
        self.default_value = default_value
        self.uuid = dpg.generate_uuid()


    def draw(self, parent: str) -> None:
        """Draw the input component on the specified parent."""
        dpg.add_input_text(
            label=self.label,
            default_value=self.default_value,
            tag=self.uuid,
            parent=parent,
        )


    def get_value(self) -> any:
        """Retrieve the current value of the input."""
        return dpg.get_value(self.uuid)
    
    