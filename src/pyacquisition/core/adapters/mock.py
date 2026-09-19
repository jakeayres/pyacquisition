"""A stand-in for pyvisa, so hardware instruments can run without the device.

Select it in the TOML config exactly as you would `pyvisa`:

    [instruments]
    lockin = {instrument = "SR_830", adapter = "mock", resource = "anything"}

The resource behaves like a pyvisa message based resource (`write`, `read`,
`query`, `close`). It has no model of any particular instrument. It answers
queries in three steps:

1. A reply you configured with `responses`, which always wins.
2. What was last written: after `SETP 1,2.5`, the query `SETP? 1` returns `2.5`,
   and after `SOUR:CURR 1e-3`, `SOUR:CURR?` returns `1e-3`. Every setter and
   getter pair therefore round-trips.
3. A default reply (`"0"` unless changed), so an unconfigured getter still
   parses as a number.

Configure replies in the config file with `args`:

    args = {responses = {"*IDN?" = "KEITHLEY INSTRUMENTS INC.,MODEL 6221,1,D03"}}
"""

from collections import deque

from pyvisa import constants
from pyvisa.errors import InvalidSession, VisaIOError


def mock_adapter():
    """Returns a resource manager whose resources are simulated."""
    return MockResourceManager()


def _normalise(message: str) -> str:
    """Collapses whitespace and case, so `"sour:curr?"` and `"SOUR:CURR? "` match."""
    return " ".join(str(message).split()).upper()


class MockResource:
    """A simulated message based resource.

    Args:
        resource_name (str): The resource string the instrument was opened with.
        responses (dict): Replies keyed by query. A key is either the whole query
            (`"SETP? 1"`) or just its header (`"SETP?"`). A value is a string or
            number (always returned), a list (returned in turn, repeating the
            last), or a callable that gets the normalised query and returns the
            reply.
        default_reply (str): The reply to a query nothing else answers.
        transcript (str): A file recorded with the `record` adapter, whose replies
            are given back in the order they were recorded. `responses` win.
        **attributes: Any other pyvisa attribute (`timeout`, `read_termination`,
            `write_termination`, `send_end`, `query_delay`...), set as given.

    Attributes:
        written (list[str]): Everything written to the resource, in order.
        state (dict[str, str]): What was last written, keyed by command header.
    """

    def __init__(
        self,
        resource_name,
        responses=None,
        default_reply="0",
        transcript=None,
        **attributes,
    ):
        self.resource_name = resource_name
        self.default_reply = str(default_reply)
        self.timeout = 2000
        self.read_termination = ""
        self.write_termination = ""
        self.send_end = True
        self.query_delay = 0.0
        for name, value in attributes.items():
            setattr(self, name, value)

        self.opened = True
        self.written = []
        self.state = {}
        self._responses = {}
        self._output = deque()
        if transcript is not None:
            from .record import load_transcript

            for message, replies in load_transcript(transcript).items():
                self._responses.setdefault(_normalise(message), []).extend(replies)
        for query, reply in (responses or {}).items():
            self.respond(query, reply)

    # ------------------------------------------------------------ configuring
    def respond(self, query, reply):
        """Sets the reply to a query, replacing any earlier reply to it.

        Args:
            query (str): The whole query (`"SETP? 1"`) or its header (`"SETP?"`).
            reply: A string or number, a list to return in turn, or a callable
                taking the normalised query and returning the reply.
        """
        self._responses[_normalise(query)] = reply

    # ------------------------------------------------------------ pyvisa API
    def write(self, message):
        """Sends a message to the simulated instrument.

        Returns:
            int: The number of bytes written, as pyvisa does.
        """
        self._require_open()
        self.written.append(message)
        header, _, arguments = message.strip().partition(" ")
        header, arguments = header.upper(), arguments.strip()

        if header.endswith("?"):
            self._output.append(self._reply(header, arguments, message))
        elif header == "*RST":
            self.state.clear()
        elif arguments:
            self._remember(header, arguments)

        return len((message + self.write_termination).encode())

    def read(self):
        """Reads the next reply.

        Raises:
            VisaIOError: If no query is waiting for a reply, as a real
                instrument would time out.
        """
        self._require_open()
        if not self._output:
            raise VisaIOError(constants.StatusCode.error_timeout)
        return self._output.popleft()

    def query(self, message, delay=None):
        """Writes a message, then reads the reply."""
        self.write(message)
        return self.read()

    def clear(self):
        """Discards any reply that has not been read."""
        self._require_open()
        self._output.clear()

    def close(self):
        self.opened = False
        self._output.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    # ------------------------------------------------------------ simulation
    def _require_open(self):
        if not self.opened:
            raise InvalidSession()

    def _remember(self, header, arguments):
        """Records a setter so its getter can return the value.

        `SOUR:CURR 1e-3` is stored under `SOUR:CURR`. `SETP 1,2.5` is stored
        under `SETP` and also, with its first argument as a channel, under
        `SETP 1`, because its getter is `SETP? 1`.
        """
        self.state[header] = arguments
        channel, comma, value = arguments.partition(",")
        if comma:
            self.state[f"{header} {channel.strip()}"] = value.strip()

    def _reply(self, header, arguments, message):
        query = _normalise(message)
        for key in (query, header):
            if key in self._responses:
                return self._resolve(key, query)

        command = header[:-1]
        key = f"{command} {arguments}" if arguments else command
        if key in self.state:
            return self.state[key]

        return self._builtin(header) or self.default_reply

    def _resolve(self, key, query):
        reply = self._responses[key]
        if callable(reply):
            reply = reply(query)
        elif isinstance(reply, (list, tuple)):
            # step through the list, holding on the last reply
            if len(reply) > 1:
                self._responses[key] = reply[1:]
            reply = reply[0]
        return str(reply)

    def _builtin(self, header):
        replies = {
            "*IDN?": f"MOCK,{self.resource_name},0,0",
            "*OPC?": "1",
            "SYST:ERR?": '0,"No error"',
            "STAT:QUE?": '0,"No error"',
        }
        return replies.get(header)


class _AnyResource(tuple):
    """The resources a manager lists, which claims to hold every name.

    `Experiment` only opens a resource that appears in `list_resources()`. A
    simulated instrument has no real address to list, so any name is accepted.
    """

    def __contains__(self, item):
        return True


class MockResourceManager:
    """Opens simulated resources, in the place of `pyvisa.ResourceManager`."""

    def __init__(self):
        self.resources = {}

    def open_resource(self, resource_name, **kwargs):
        """Opens a simulated resource. Keyword arguments go to `MockResource`."""
        resource = MockResource(resource_name, **kwargs)
        self.resources[resource_name] = resource
        return resource

    def list_resources(self, query="?*::INSTR"):
        return _AnyResource(self.resources)

    def close(self):
        for resource in self.resources.values():
            resource.close()
        self.resources.clear()
