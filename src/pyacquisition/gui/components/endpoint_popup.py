import dearpygui.dearpygui as dpg
import asyncio
import json
from .inputs.integer_input import IntegerInput
from .inputs.string_input import StringInput
from .inputs.boolean_input import BooleanInput
from .inputs.float_input import FloatInput
from .inputs.enum_input import EnumInput
from .inputs.base_input import BaseInput
from .text import add_text, add_header, add_text_area
from .input_group import InputGroup
from ..api_client import APIClient


class EndpointPopup:
    """Class to create a popup for FastAPI endpoints."""
    
    def __init__(self, api_client, path) -> None:
        self.uuid = dpg.generate_uuid()
        self.api_client = api_client
        self.path = path
        self.input_group = InputGroup()
        self.inputs = []
        self.response_text_area = None 
        
        for param in self.path.get.parameters.values():
            input_component = self.param_to_input(param)
            self.add_input(input_component)
            
            self.input_group.add_input(input_component)
            
            
    def param_to_input(self, param: str) -> BaseInput:
        """Convert a parameter type to the corresponding input component."""
        if param.type_ == "integer":
            return IntegerInput(param.name, default_value=0)
        elif param.type_ == "string":
            return StringInput(param.name, default_value="")
        elif param.type_ == "number":
            return FloatInput(param.name, default_value=0.0)
        elif param.type_ == "boolean":
            return BooleanInput(param.name, default_value=False)
        elif param.type_ == "enum":
            return EnumInput(param.name, options=param.enum_values, default_value=param.enum_values[0])
        else:
            raise ValueError(f"Unsupported parameter type: {param.type_}")


    def add_input(self, input_component: BaseInput) -> None:
        """Add an input component to the popup."""
        self.inputs.append(input_component)


    def draw(self) -> None:
        """Draw the popup and its inputs."""
        with dpg.window(
            label=f"{self.path.get.summary}",
            width=300,
            height=-1,
            modal=False,
            show=True,
            tag=self.uuid,
        ):
            add_text(self.path.get.description, wrap=265)

            if self.input_group.length > 0:
                add_header("Parameters")
                self.input_group.draw()
                
            
            dpg.add_button(
                label="Send Request",
                callback=self.request,
                indent=10,
            )
            
            dpg.add_spacer(height=5)
            add_header("Response")
            self.response_text_area = add_text_area(height=200, width=265)
            


    def run_async(self, func) -> None:
        """Run an async function in the event loop."""
        asyncio.create_task(func)


    def get_input_data(self) -> dict:
        """Retrieve data from all inputs."""
        return {input_component.label: input_component.get_value() for input_component in self.inputs}
    
    
    def request(self) -> None:
        """Send a request to the endpoint with the input data."""
        data = self.get_input_data()
        response = self.api_client.get(endpoint=self.path.path, params=data)
        dpg.set_value(self.response_text_area, json.dumps(response, indent=2))