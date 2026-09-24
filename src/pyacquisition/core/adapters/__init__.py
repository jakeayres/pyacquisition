from .mock import mock_adapter
from .prologix import prologix_adapter
from .pyvisa import pyvisa_adapter
from .record import record_adapter

_adapters = {
    "pyvisa": pyvisa_adapter,
    "mock": mock_adapter,
    "prologix": prologix_adapter,
    "record": record_adapter,
}

DEFAULT_ADAPTER = "pyvisa"
DEFAULT_TIMEOUT = 5000


def get_adapter(adapter_name: str):
    """Get the adapter class by name."""

    if adapter_name in _adapters:
        return _adapters[adapter_name]()
    else:
        raise ValueError(f"Adapter {adapter_name} not found.")


def open_resource(
    resource: str,
    adapter: str = DEFAULT_ADAPTER,
    timeout: int = DEFAULT_TIMEOUT,
    **kwargs,
):
    """Open a resource through an adapter.

    Args:
        resource (str): The address of the instrument, in the form the adapter
            expects, such as `GPIB0::7::INSTR` for `pyvisa` or `COM3::7` for
            `prologix`.
        adapter (str): The name of the adapter. Defaults to `"pyvisa"`.
        timeout (int): How long to wait for the instrument to reply, in
            milliseconds. Defaults to 5000.
        **kwargs: Passed to the adapter's `open_resource`, for example
            `read_termination`.

    Returns:
        The opened resource, which has the same interface as a pyvisa resource.

    Raises:
        ValueError: If there is no adapter with that name.
        ConnectionError: If the resource cannot be opened. The message lists the
            resources the adapter can see, when it can say.
    """
    manager = get_adapter(adapter)
    try:
        return manager.open_resource(resource, timeout=timeout, **kwargs)
    except Exception as error:
        raise ConnectionError(
            f"Could not open '{resource}' with the {adapter} adapter: {error}"
            f"{_available(manager)}"
        ) from error


def _available(manager) -> str:
    """Describes what the adapter can see, for an error message."""
    try:
        found = sorted(str(name) for name in manager.list_resources())
    except Exception:  # noqa: BLE001 - the hint must never hide the real error
        return ""
    if not found:
        return " No resources were found."
    return f" Available resources: {', '.join(found)}."
