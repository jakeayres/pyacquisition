import dearpygui.dearpygui as dpg
from .inputs.base_input import BaseInput


class InputGroup:
    
    
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
        """Draw all input components in the group."""
        for input_component in self.inputs:
            input_component.draw()
            dpg.add_spacer(height=5)