import dearpygui.dearpygui as dpg
import asyncio
import json
from .inputs.integer_input import IntegerInput
from .inputs.string_input import StringInput
from .inputs.boolean_input import BooleanInput
from .inputs.float_input import FloatInput
from .inputs.enum_input import EnumInput
from .inputs.base_input import BaseInput
from ..api_client import APIClient


class EndpointPopup:
    """Class to create a popup for FastAPI endpoints."""
    
    def __init__(self, api_client, path) -> None:
        self.uuid = dpg.generate_uuid()
        self.api_client = api_client
        self.path = path
        self.inputs = []  # List to store input components
        self.response_text_area = None  # Text area for displaying the response
        
        for param in self.path.get.parameters.values():
            input_component = self.param_to_input(param)
            self.add_input(input_component)
            
            
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
            dpg.add_text(f"{self.path.get.description}", color=(200, 200, 200), wrap=300)
            dpg.add_spacer(height=10)
            dpg.add_separator()
            dpg.add_spacer(height=10)
            
            if len(self.inputs) > 0:
                dpg.add_text(f"Parameters:", color=(255, 255, 255))
                dpg.add_spacer(height=10)
                for input_component in self.inputs:
                    input_component.draw(parent=self.uuid)
                dpg.add_spacer(height=10)
            
            dpg.add_button(
                label="Send Request",
                callback=self.request,
            )
            
            dpg.add_spacer(height=10)
            dpg.add_separator()
            dpg.add_spacer(height=5)
            
            dpg.add_text(f"Response:", color=(255, 255, 255))
            
            self.response_text_area = dpg.add_input_text(
                multiline=True,
                readonly=True,
                height=100,  # Adjust height as needed
                width=280,   # Adjust width as needed
            )
            
            print(self.response_text_area)


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