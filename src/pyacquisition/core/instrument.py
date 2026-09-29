from functools import partial, wraps
import inspect
import typing
from enum import Enum

from .adapters import DEFAULT_ADAPTER, open_resource


class BaseEnum(Enum):
    """Base class for Enums used as args in query/command methods."""

    def __init__(self, raw_value, label):
        self.raw_value = raw_value
        self.label = label

    @property
    def value(self):
        return self.label

    @classmethod
    def from_raw_value(cls, raw_value):
        for item in cls:
            if item.raw_value == raw_value:
                return item
        raise ValueError(f"Invalid raw value: {raw_value}")

    @classmethod
    def from_label(cls, label):
        for item in cls:
            if item.label == label:
                return item
        raise ValueError(f"Invalid label: {label}")


def enum_classes(annotation) -> list:
    """The enums that an annotation allows: the enum itself, or those in a union."""
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return [annotation]
    found = []
    for argument in typing.get_args(annotation):
        found += enum_classes(argument)
    return found


def _allows_text(annotation) -> bool:
    return annotation is str or str in typing.get_args(annotation)


def _plain(text: str) -> str:
    """Text with case, spaces, hyphens and underscores taken out, to compare."""
    return "".join(c for c in text.lower() if c not in " _-")


def _member(enums: list, text: str):
    """The member of the enums that `text` names, or None.

    A member is named by its name (`"INPUT_A"`) or, for a `BaseEnum`, by the label
    that the interface shows (`"Input A"`), in either case, with spaces or underscores.
    """
    for enum in enums:
        for member in enum:
            if member.name == text:
                return member
    wanted = _plain(text)
    found = []
    for enum in enums:
        for member in enum:
            names = [member.name, getattr(member, "label", None), member.value]
            if wanted in [_plain(n) for n in names if isinstance(n, str)]:
                found.append(member)
    # Enums that are copies of one another, such as the two Lakeshores' channels, have
    # members of the same names, and they are one answer, not two.
    if len({m.name for m in found}) > 1:
        options = ", ".join(f"{m.__class__.__name__}.{m.name}" for m in found)
        raise ValueError(f"{text!r} could mean any of {options}. Give the exact name.")
    return found[0] if found else None


def resolve_enum_kwargs(function, kwargs: dict) -> dict:
    """Turns text into the enum members that a function's parameters take.

    A parameter that is annotated with an `Enum` (`input_channel: InputChannel`),
    and is given a string, gets the member that the string names, so
    `input_channel="INPUT_A"` does what `input_channel=InputChannel.INPUT_A` does.
    The string is a member's name or its label, in either case, and spaces and
    underscores do not matter: `"INPUT_A"`, `"Input A"` and `"input a"` all work.
    Everything else is passed on unchanged, including members.

    Args:
        function (callable): The function that will be called.
        kwargs (dict): The keyword arguments it will be called with.

    Returns:
        dict: The keyword arguments, with the strings resolved.

    Raises:
        ValueError: If a string does not name a member, which says what would.
    """
    if not any(isinstance(value, str) for value in kwargs.values()):
        return dict(kwargs)
    try:
        parameters = inspect.signature(function).parameters
    except (TypeError, ValueError):
        return dict(kwargs)
    try:
        hints = typing.get_type_hints(function)
    except Exception:  # noqa: BLE001 - a partial, or a hint that cannot be resolved
        hints = {}

    resolved = {}
    for key, value in kwargs.items():
        if isinstance(value, str) and key in parameters:
            annotation = hints.get(key, parameters[key].annotation)
            enums = enum_classes(annotation)
            if enums:
                member = _member(enums, value)
                if member is not None:
                    value = member
                elif not _allows_text(annotation):
                    names = ", ".join(m.name for enum in enums for m in enum)
                    raise ValueError(f"`{key}`: {value!r} is not one of {names}")
        resolved[key] = value
    return resolved


class QueryCommandProvider(type):
    """Metaclass that reads through methods and registers
    those that are decorated as queries"""

    def __init__(cls, name, bases, attrs):
        queries = set()
        commands = set()
        traces = set()

        for name, method in attrs.items():
            if isinstance(method, property):
                method = method.fget

            if hasattr(method, "_is_query"):
                queries.add(method)

            elif hasattr(method, "_is_command"):
                commands.add(method)

            elif hasattr(method, "_is_trace"):
                traces.add(method)

        cls._queries = queries
        cls._commands = commands
        cls._traces = traces

        # The name the interface shows for the instrument: the driver's own, or
        # else its class name (SR_830), not a name inherited from its base class.
        if "name" not in attrs:
            cls.name = cls.__name__


def mark_query(func):
    """Decorator for marking method as a query"""
    func._is_query = True
    return func


def mark_command(func):
    """Decorator for marking method as a query"""
    func._is_command = True
    return func


def mark_trace(func=None, *, start=None, ready=None, stop=None, timeout=None, channels=None):
    """Marks a method that returns a trace, a `TraceData` (see core/trace.py).

    Use it bare, `@mark_trace`, for a trace that is fetched at once, or name the
    phases of one that takes time to acquire, by the methods that do them:

        @mark_trace(start="start_sweep", ready="sweep_done", stop="abort_sweep", timeout=300)
        def get_sweep(self) -> TraceData: ...

    The trace is then taken by calling `start`, then `ready` every 0.1 s until
    it is true, then the method itself, to fetch it. If it is cancelled (an
    aborted task, the experiment stopping) or takes longer than `timeout`
    seconds, `stop` is called, so the instrument isn't left acquiring.

    `channels` names the channels its traces have, so that their columns (a
    reduction's, see `Trace`) are known before the first is taken: a list, or
    the name of a method that gives it, for channels that depend on a setting.
    Without it, a trace is taken to have one channel.

    A trace method isn't an instrument endpoint: it is taken through the trace's
    own (`/traces/...`).
    """

    def mark(method):
        method._is_trace = True
        method._trace_phases = {"start": start, "ready": ready, "stop": stop}
        method._trace_timeout = timeout
        method._trace_channels = channels
        return method

    return mark(func) if func is not None else mark


def has_cache(func):
    """Add cache functionality (save last result only)"""
    func._cached = [0]

    @wraps(func)  # This passes the func metadata onto wrapper
    def wrapper(*args, from_cache=False, **kwargs):
        if from_cache:
            return func._cached[0]
        else:
            result = func(*args, **kwargs)
            func._cached[0] = result
            return result

    return wrapper


class Instrument(metaclass=QueryCommandProvider):
    """Base instrument class to be inherited by hardware instruments.

    Wraps a visa resource, which is either opened for you from an address or
    passed in already open.

    Args:
        uid (str): The id of the instrument, used in the interface, the API and
            in tasks.
        resource (str | resource): The address of the instrument, such as
            `"GPIB0::7::INSTR"`, or a resource that is already open. An address
            is opened through `adapter`. A resource that was passed in stays
            yours to close.
        adapter (str): How to reach the instrument: `"pyvisa"` (the default),
            `"prologix"`, `"mock"` or `"record"`. Only for an address.
        **resource_kwargs (object): Options for opening the resource, such as `timeout`
            (in milliseconds, 5000 by default) or `read_termination`. Only for
            an address.

    Raises:
        ConnectionError: If the address cannot be opened.
        ValueError: If there is no such adapter.
        TypeError: If `adapter` or options are given with a resource that is
            already open.

    Example:
        lockin = SR_830("lockin", "GPIB0::7::INSTR")
        cryostat = Lakeshore_350("cryostat", "COM3::12", adapter="prologix")
    """

    name = "Base Instrument"

    def __init__(self, uid, resource, adapter=None, **resource_kwargs):
        self._uid = uid
        self._owns_resource = isinstance(resource, str)
        if self._owns_resource:
            resource = open_resource(
                resource, adapter or DEFAULT_ADAPTER, **resource_kwargs
            )
        elif adapter is not None or resource_kwargs:
            raise TypeError(
                "`adapter` and resource options only apply when the resource is "
                "an address. This resource is already open."
            )
        self._visa_resource = resource

    def close(self):
        """Closes the resource, if this instrument opened it.

        A resource that was passed in already open is left for its owner to
        close. Closing twice does nothing.
        """
        if self._owns_resource:
            self._owns_resource = False
            self._visa_resource.close()

    @property
    def metadata(self):
        return {
            "id": self._uid,
            "class": self.__class__.__name__,
            "address": self._visa_resource.resource_name,
        }

    @property
    def queries(self):
        """return dictionary of registered queries as externally executable partials"""
        return {q.__name__: partial(q, self) for q in self._queries}

    @property
    def commands(self):
        """return dictionary of registered commands as externally executable partials"""
        return {c.__name__: partial(c, self) for c in self._commands}

    @property
    def traces(self) -> dict[str, callable]:
        """The methods marked `@mark_trace`, by name, bound to this instrument."""
        return {t.__name__: getattr(self, t.__name__) for t in self._traces}

    def query(self, query_string, *args, **kwargs):
        """Send a query to visa resource"""
        return self._visa_resource.query(query_string, *args, **kwargs)

    def command(self, command_String, *args, **kwargs):
        """Send a command to visa resource"""
        return self._visa_resource.write(command_String, *args, **kwargs)

    def register_endpoints(self, api_server):
        @api_server.app.get(f"/{self._uid}/" + "queries/", tags=[self._uid])
        def queries() -> list[str]:
            return [name for name, _ in self.queries.items()]

        @api_server.app.get(f"/{self._uid}/" + "commands/", tags=[self._uid])
        def commands() -> list[str]:
            return [name for name, _ in self.commands.items()]

        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, "_is_query"):
                endpoint_path = f"/{self._uid}/{name}"
                endpoint_func = api_server.create_endpoint_function(method)
                api_server.app.add_api_route(
                    endpoint_path,
                    endpoint_func,
                    methods=["GET"],
                    tags=["tasks"],
                )

            if hasattr(method, "_is_command"):
                endpoint_path = f"/{self._uid}/{name}"
                endpoint_func = api_server.create_endpoint_function(method)
                api_server.app.add_api_route(
                    endpoint_path,
                    endpoint_func,
                    methods=["GET"],
                    tags=["tasks"],
                )


class SoftwareInstrument(metaclass=QueryCommandProvider):
    """Base class for software (non-hardware) instruments.

    Does not wrap a visa resource.
    """

    name = "Software Instrument"

    def __init__(self, uid):
        self._uid = uid

    def close(self):
        """Does nothing, as there is no connection. Present so that every
        instrument can be closed the same way."""

    @property
    def queries(self) -> dict[str, callable]:
        """return dictionary of registered queries as externally executable partials"""
        return {q.__name__: partial(q, self) for q in self._queries}

    @property
    def commands(self) -> dict[str, callable]:
        """return dictionary of registered commands as externally executable partials"""
        return {c.__name__: partial(c, self) for c in self._commands}

    @property
    def traces(self) -> dict[str, callable]:
        """The methods marked `@mark_trace`, by name, bound to this instrument."""
        return {t.__name__: getattr(self, t.__name__) for t in self._traces}

    @mark_query
    def identify(self):
        return self.name

    def register_endpoints(self, api_server):
        @api_server.app.get(f"/{self._uid}/" + "queries/", tags=[self._uid])
        def list_queries() -> dict:
            """Return a list of available queries"""
            return {
                "status": 200,
                "data": [name for name, _ in self.queries.items()],
            }

        @api_server.app.get(f"/{self._uid}/" + "commands/", tags=[self._uid])
        def list_commands() -> dict:
            """Return a list of available commands"""
            return {
                "status": 200,
                "data": [name for name, _ in self.commands.items()],
            }

        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, "_is_query"):
                endpoint_path = f"/{self._uid}/{name}"
                endpoint_func = api_server.create_endpoint_function(method)
                api_server.app.add_api_route(
                    endpoint_path,
                    endpoint_func,
                    methods=["GET"],
                    tags=["tasks"],
                )

            if hasattr(method, "_is_command"):
                endpoint_path = f"/{self._uid}/{name}"
                endpoint_func = api_server.create_endpoint_function(method)
                api_server.app.add_api_route(
                    endpoint_path,
                    endpoint_func,
                    methods=["GET"],
                    tags=["tasks"],
                )
