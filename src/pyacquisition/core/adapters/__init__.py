from .pyvisa import pyvisa_adapter
from .mock import mock_adapter 

_adapters = {
    'pyvisa': pyvisa_adapter,
    'mock': mock_adapter,
}

def get_adapter(adapter_name: str):
    """Get the adapter class by name."""

    if adapter_name in _adapters:
        return _adapters[adapter_name]()
    else:
        raise ValueError(f"Adapter {adapter_name} not found.")