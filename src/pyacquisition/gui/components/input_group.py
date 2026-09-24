import dearpygui.dearpygui as dpg
from .inputs.base_input import BaseInput
from ..constants import SECONDARY_COLOR

CHAR_WIDTH = 7  # of the default font
MAX_LABEL_WIDTH = 150


class InputGroup:
    """
    A form: a row for each input, with its name on the left and the box on the right.
    """

    def __init__(self):
        self.inputs = []

    @property
    def length(self):
        """Return the number of input components in the group."""
        return len(self.inputs)

    def add_input(self, input_component):
        """Add an input component to the group."""
        if not isinstance(input_component, BaseInput):
            raise ValueError("Input component must be an instance of BaseInput")
        self.inputs.append(input_component)

    def get_data(self):
        """Retrieve data from all input components."""
        data = {}
        for input_component in self.inputs:
            data[input_component.label] = input_component.get_value()
        return data

    def reset(self):
        """Reset all input components to their default values."""
        for input_component in self.inputs:
            input_component.reset()

    def draw(self, parent: str = None):
        """
        Draw the form. The names are as wide as the longest one, up to a limit, and
        the boxes share the rest of the width. Hovering over a name shows the hint
        of its input, if it has one.
        """
        longest = max((len(i.label) for i in self.inputs), default=0)
        label_width = min(longest * CHAR_WIDTH + 12, MAX_LABEL_WIDTH)

        options = {"parent": parent} if parent is not None else {}
        with dpg.table(
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            borders_innerH=False,
            borders_innerV=False,
            borders_outerH=False,
            borders_outerV=False,
            pad_outerX=False,
            **options,
        ) as table:
            dpg.add_table_column(width_fixed=True, init_width_or_weight=label_width)
            dpg.add_table_column(width_stretch=True, init_width_or_weight=1.0)
            for input_component in self.inputs:
                with dpg.table_row():
                    name = dpg.add_text(input_component.label, color=SECONDARY_COLOR)
                    input_component.draw()
                    if input_component.hint:
                        with dpg.tooltip(name):
                            dpg.add_text(input_component.hint)
        return table
