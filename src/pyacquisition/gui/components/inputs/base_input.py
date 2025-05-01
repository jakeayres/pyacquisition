import dearpygui.dearpygui as dpg


class BaseInput:
    """Base class for input components."""

    
    
    def __init__(self, label: str, default_value=None) -> None:
        self.label = label
        self.default_value = default_value
        self.uuid = dpg.generate_uuid()
        

    def draw(self, parent: str | None = None) -> None:
        """Draw the input component, optionally on the specified parent."""
        kwargs = dict(
            label=self.label,
            default_value=self.default_value,
            tag=self.uuid,
            indent=10,
        )
        if parent is not None:
            kwargs["parent"] = parent
        return dpg.add_input_text(**kwargs)
        
        
    def reset(self) -> None:
        """Reset the input component to its default value."""
        dpg.set_value(self.uuid, self.default_value)


    def get_value(self) -> any:
        """Retrieve the current value of the input."""
        return dpg.get_value(self.uuid)


