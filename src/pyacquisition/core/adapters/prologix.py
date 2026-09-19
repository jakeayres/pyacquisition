"""Adapter for the Prologix GPIB-USB controller.

The controller appears as a virtual COM port. This adapter gives the instruments
attached to it the same interface as a `pyvisa` GPIB resource (`write`, `read`,
`query`, `close`, `timeout`, `read_termination`...), so an instrument class works
the same over either. Select it in the TOML config:

    [instruments]
    lockin = {instrument = "SR_830", adapter = "prologix", resource = "COM3::7"}

The resource string is `<serial port>::<GPIB address>[::<secondary address>]`,
for example `COM3::12`, `/dev/ttyUSB0::12` or `COM3::9::0`. A trailing `::INSTR`
is accepted. Options such as `read_termination` or `timeout` are passed with
`args`, exactly as for `pyvisa`.

How it matches a direct GPIB connection:

- The defaults are pyvisa's: writes end in CR+LF with EOI asserted on the last
  byte, and a read ends on EOI, unless `read_termination` is set.
- Instruments share one controller. A controller is opened once per serial port,
  and every write or query runs under a lock, so instruments used from several
  threads cannot mix up their replies.
- The controller keeps a single configuration (manual, section 5). Each
  resource re-applies its own address, EOI, timeout and read mode whenever the
  bus switches to it.

Notes:

- A message that ends on EOI is marked with a sentinel byte (ASCII 4, EOT), so an
  instrument that replies in binary must not send that byte. An instrument that
  does not assert EOI needs `read_termination` set.
- The controller waits at most 3000 ms for a reply (manual, 8.12). A longer
  `timeout` is honoured by asking again until it runs out.
"""

import math
import os
import re
import threading
import time

from pyvisa import constants
from pyvisa.errors import InvalidSession, VisaIOError

# The controller appends this byte to a reply when it sees EOI (`++eot_char`).
SENTINEL = 4

_ESC = 27
# Bytes the controller treats specially, so they are escaped in data (manual, 7).
_NEEDS_ESCAPE = frozenset({10, 13, 27, 43})

# The longest `++read_tmo_ms` the controller accepts (manual, 8.12).
_MAX_READ_TMO_MS = 3000
# How much longer than the controller's own timeout to wait for its reply.
_MARGIN = 0.05

_RESOURCE = re.compile(
    r"^(?P<port>.+?)::(?P<pad>\d+)(?:::(?P<sad>\d+))?(?:::INSTR)?$", re.IGNORECASE
)

_ATTRIBUTES = frozenset(
    {
        "timeout",
        "read_termination",
        "write_termination",
        "send_end",
        "encoding",
        "query_delay",
    }
)


def prologix_adapter():
    """Returns a resource manager for instruments behind a Prologix controller."""
    return PrologixResourceManager()


def parse_resource(resource_name):
    """Splits a resource string into its serial port and GPIB addresses.

    Returns:
        tuple: The port, the primary address (0 to 30) and the secondary address
            (96 to 126, or None). A secondary address given as 0 to 30, as pyvisa
            does, is converted.

    Raises:
        ValueError: If the string is not `<port>::<address>[::<secondary>]`.
    """
    match = _RESOURCE.match(str(resource_name).strip())
    if match is None:
        raise ValueError(
            f"Invalid Prologix resource {resource_name!r}, "
            "expected '<serial port>::<GPIB address>', for example 'COM3::12'"
        )
    primary = int(match["pad"])
    if not 0 <= primary <= 30:
        raise ValueError(f"GPIB address {primary} is not between 0 and 30")

    secondary = None
    if match["sad"] is not None:
        secondary = int(match["sad"])
        if secondary <= 30:
            secondary += 96
        if not 96 <= secondary <= 126:
            raise ValueError(f"GPIB secondary address {match['sad']} is not valid")
    return match["port"], primary, secondary


def _escape(data):
    """Escapes the bytes the controller would otherwise act on."""
    escaped = bytearray()
    for byte in data:
        if byte in _NEEDS_ESCAPE:
            escaped.append(_ESC)
        escaped.append(byte)
    return bytes(escaped)


def _timeout_error():
    return VisaIOError(constants.StatusCode.error_timeout)


def _open_serial(port):
    import serial

    return serial.Serial(port, baudrate=115200, timeout=0.02, write_timeout=2)


def _list_ports():
    from serial.tools import list_ports

    return [port.device for port in list_ports.comports()]


def _key(port):
    return port.upper() if os.name == "nt" else port


class PrologixController:
    """One Prologix controller, shared by every instrument on its GPIB bus.

    Use `lock` around any exchange with an instrument, so the address, the
    configuration and the reply all belong to the same instrument.
    """

    def __init__(self, port, serial_port):
        self.port = port
        self.lock = threading.RLock()
        self.references = 0
        self._serial = serial_port
        self._applied = {}
        self._initialise()

    def _initialise(self):
        self._serial.reset_input_buffer()
        self.send("++ver")
        reply = self.collect(b"\n", wait=1.0)
        if reply is None or b"prologix" not in reply.lower():
            raise ConnectionError(f"No Prologix controller answered on {self.port}")

        self.configure(
            {
                # first, so that changing settings below does not wear the EEPROM
                "savecfg": "0",
                "mode": "1",
                # read only when asked, so setters do not provoke a talk cycle
                "auto": "0",
                # the terminator is sent as data, as pyvisa sends it
                "eos": "3",
                "eot_char": str(SENTINEL),
            }
        )

    def send(self, command):
        """Sends a `++` command to the controller."""
        self._serial.write(command.encode("ascii") + b"\n")

    def send_data(self, data):
        """Sends bytes to the addressed instrument."""
        self._serial.write(_escape(data) + b"\n")

    def configure(self, settings):
        """Applies the settings that differ from what the controller already has."""
        for name, value in settings.items():
            if self._applied.get(name) != value:
                self.send(f"++{name} {value}")
                self._applied[name] = value

    def discard_input(self):
        """Drops anything the controller sent that nobody asked for."""
        self._serial.reset_input_buffer()

    def collect(self, marker, wait, keep_marker=True):
        """Reads until `marker` arrives.

        Args:
            marker (bytes): What ends the message.
            wait (float): How long the controller may stay silent, in seconds.
            keep_marker (bool): Whether the returned bytes include the marker.

        Returns:
            bytes: The message, or None if nothing arrived at all.

        Raises:
            VisaIOError: If a message started and then stopped without its marker.
        """
        buffer = bytearray()
        last = time.monotonic()
        while True:
            chunk = self._serial.read(max(1, self._serial.in_waiting))
            now = time.monotonic()
            if chunk:
                buffer += chunk
                last = now
                index = buffer.find(marker)
                if index >= 0:
                    return bytes(buffer[: index + (len(marker) if keep_marker else 0)])
            elif now - last >= wait:
                if buffer:
                    raise _timeout_error()
                return None

    def close(self):
        self._serial.close()


_controllers = {}
_registry_lock = threading.Lock()


def _acquire(port):
    """Returns the controller for a port, opening the port on first use."""
    with _registry_lock:
        controller = _controllers.get(_key(port))
        if controller is None:
            serial_port = _open_serial(port)
            try:
                controller = PrologixController(port, serial_port)
            except Exception:
                serial_port.close()
                raise
            _controllers[_key(port)] = controller
        controller.references += 1
        return controller


def _release(controller):
    """Gives a controller back, closing its port when nothing uses it."""
    with _registry_lock:
        controller.references -= 1
        if controller.references <= 0:
            _controllers.pop(_key(controller.port), None)
            controller.close()


class PrologixResource:
    """An instrument on a Prologix controller, used like a pyvisa GPIB resource.

    Args:
        controller (PrologixController): The controller the instrument is on.
        resource_name (str): The resource string it was opened with.
        primary (int): The GPIB address.
        secondary (int): The GPIB secondary address, if any.
        **attributes: `timeout` (ms), `read_termination`, `write_termination`,
            `send_end`, `encoding` and `query_delay`, with the pyvisa defaults.
    """

    def __init__(
        self, controller, resource_name, primary, secondary=None, **attributes
    ):
        unknown = set(attributes) - _ATTRIBUTES
        if unknown:
            raise ValueError(f"Unknown resource attributes: {sorted(unknown)}")

        self.controller = controller
        self.resource_name = resource_name
        self.primary = primary
        self.secondary = secondary
        self.timeout = 2000
        self.read_termination = None
        self.write_termination = "\r\n"
        self.send_end = True
        self.encoding = "ascii"
        self.query_delay = 0.0
        for name, value in attributes.items():
            setattr(self, name, value)
        self.opened = True

    # ------------------------------------------------------------ pyvisa API
    def write_raw(self, data):
        """Writes bytes to the instrument.

        Returns:
            int: The number of bytes written.
        """
        self._require_open()
        with self.controller.lock:
            self.controller.configure(self._settings(self.read_termination))
            self.controller.send_data(data)
        return len(data)

    def write(self, message, termination=None, encoding=None):
        """Writes a message, followed by the write termination.

        Returns:
            int: The number of bytes written.
        """
        term = self.write_termination if termination is None else termination
        if term:
            message += term
        return self.write_raw(message.encode(encoding or self.encoding))

    def read_raw(self):
        """Reads a message as bytes."""
        return self._read_bytes(self.read_termination)

    def read(self, termination=None, encoding=None):
        """Reads a message, up to EOI or the read termination.

        Returns:
            str: The message, without the read termination.

        Raises:
            VisaIOError: If no message arrives within `timeout`.
        """
        term = self.read_termination if termination is None else termination
        message = self._read_bytes(term).decode(encoding or self.encoding)
        if term and message.endswith(term):
            return message[: -len(term)]
        return message

    def query(self, message, delay=None):
        """Writes a message, then reads the reply."""
        with self.controller.lock:  # nobody else gets in between the two
            self.write(message)
            delay = self.query_delay if delay is None else delay
            if delay > 0.0:
                time.sleep(delay)
            return self.read()

    def clear(self):
        """Sends Selected Device Clear to the instrument."""
        self._exchange("++clr")

    def assert_trigger(self):
        """Sends a Group Execute Trigger to the instrument."""
        self._exchange("++trg")

    def read_stb(self):
        """Serial polls the instrument.

        Returns:
            int: The status byte.
        """
        with self.controller.lock:
            self._exchange("++spoll")
            reply = self.controller.collect(b"\n", self._wait())
        if reply is None:
            raise _timeout_error()
        return int(reply)

    def close(self):
        if self.opened:
            self.opened = False
            _release(self.controller)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    # ------------------------------------------------------------ internals
    def _require_open(self):
        if not self.opened:
            raise InvalidSession()

    def _exchange(self, command):
        """Sends a controller command to this instrument, with its settings."""
        self._require_open()
        with self.controller.lock:
            self.controller.configure(self._settings(self.read_termination))
            self.controller.discard_input()
            self.controller.send(command)

    def _read_tmo_ms(self):
        """The controller's read timeout, which is capped at 3000 ms."""
        timeout = self.timeout
        if timeout is None or math.isinf(timeout):
            return _MAX_READ_TMO_MS
        return max(1, min(int(timeout), _MAX_READ_TMO_MS))

    def _wait(self):
        """How long to wait for the controller to answer one `++read`, in seconds."""
        return self._read_tmo_ms() / 1000 + _MARGIN

    def _settings(self, termination):
        """The controller settings this instrument needs."""
        address = str(self.primary)
        if self.secondary is not None:
            address += f" {self.secondary}"
        return {
            "addr": address,
            "eoi": "1" if self.send_end else "0",
            "read_tmo_ms": str(self._read_tmo_ms()),
            # EOI is reported with the sentinel, unless a termination is used
            "eot_enable": "0" if termination else "1",
        }

    def _read_bytes(self, termination):
        self._require_open()
        if termination:
            end = termination.encode(self.encoding)
            command, marker, keep_marker = f"++read {end[-1]}", end, True
        else:
            command, marker, keep_marker = "++read eoi", bytes([SENTINEL]), False

        timeout = math.inf if self.timeout is None else self.timeout / 1000
        deadline = time.monotonic() + timeout

        with self.controller.lock:
            self.controller.configure(self._settings(termination))
            self.controller.discard_input()
            while True:
                self.controller.send(command)
                remaining = deadline - time.monotonic()
                message = self.controller.collect(
                    marker,
                    wait=min(self._wait(), max(remaining, _MARGIN)),
                    keep_marker=keep_marker,
                )
                if message is not None:
                    return message
                # The controller gives up after 3 s, so ask again until the
                # instrument's own timeout has passed.
                if time.monotonic() >= deadline:
                    raise _timeout_error()


class _Resources(tuple):
    """The serial ports that can hold a controller.

    The controller cannot scan its bus, so instead of instruments this lists the
    ports. `"COM3::12" in resources` is true when `COM3` is a port and 12 a valid
    GPIB address, which is what `Experiment` checks before it opens a resource.
    """

    def __contains__(self, item):
        try:
            port = parse_resource(item)[0]
        except (ValueError, TypeError):
            return False
        return any(_key(port) == _key(known) for known in self)


class PrologixResourceManager:
    """Opens instruments on Prologix controllers, in place of `pyvisa.ResourceManager`."""

    def __init__(self):
        self.resources = {}

    def list_resources(self, query="?*::INSTR"):
        return _Resources(_list_ports())

    def open_resource(self, resource_name, **kwargs):
        """Opens the instrument at a GPIB address behind a controller.

        Keyword arguments are resource attributes, as for pyvisa. The arguments
        that only make sense for VISA (`access_mode`, `open_timeout`,
        `resource_pyclass`) are ignored.
        """
        port, primary, secondary = parse_resource(resource_name)
        for ignored in ("access_mode", "open_timeout", "resource_pyclass"):
            kwargs.pop(ignored, None)

        controller = _acquire(port)
        try:
            resource = PrologixResource(
                controller, resource_name, primary, secondary, **kwargs
            )
        except Exception:
            _release(controller)
            raise
        self.resources[resource_name] = resource
        return resource

    def close(self):
        for resource in self.resources.values():
            resource.close()
        self.resources.clear()
