from .base_input import BaseInput
import dearpygui.dearpygui as dpg


class EnumInput(BaseInput):
    """Enum input component with a dropdown box for selecting valid options."""
    
    def __init__(self, label: str, options: list[str], default_value: str = None) -> None:
        """
        Initialize the EnumInput.

        :param label: The label for the dropdown.
        :param options: A list of valid options for the dropdown.
        :param default_value: The default selected value (must be in options).
        """
        if default_value is None:
            default_value = options[0] if options else ""
        if default_value not in options:
            raise ValueError("Default value must be one of the options.")
        
        super().__init__(label, default_value)
        self.options = options

    def draw(self) -> None:
        """Draw the enum input (dropdown) on the specified parent."""

        print(self.options)
        print(self.default_value)

        dpg.add_combo(
            label=self.label,
            items=self.options,
            default_value=self.default_value,
            indent=10,
            tag=self.uuid,
        )