import threading
import time

import pytest
from pyvisa.errors import InvalidSession, VisaIOError

from pyacquisition import Experiment
from pyacquisition.core.adapters import get_adapter, prologix
from pyacquisition.core.adapters.mock import MockResource
from pyacquisition.core.adapters.prologix import (
    SENTINEL,
    PrologixResourceManager,
    parse_resource,
)
from pyacquisition.instruments import Keithley_6221, Lakeshore_350
from pyacquisition.instruments.keithley.keithley_6221 import State
from pyacquisition.instruments.lakeshore.lakeshore_350 import OutputChannel


class FakePrologix:
    """The serial port of a Prologix controller with instruments on its GPIB bus.

    It follows the manual: `++` commands configure it, data is unescaped and sent
    to the instrument at the current address, and nothing comes back until
    `++read`, unless `++auto 1`. Instruments are GPIB devices with `write(str)`
    and `read()`, and terminate their replies with LF and EOI.
    """

    def __init__(
        self, instruments, version="Prologix GPIB-USB Controller version 6.91"
    ):
        self.timeout = 0.02
        self.instruments = instruments
        self.version = version
        self.config = {
            "mode": "1",
            "auto": "1",
            "eoi": "1",
            "eos": "0",
            "eot_enable": "0",
            "eot_char": "0",
            "read_tmo_ms": "500",
            "savecfg": "1",
            "addr": "0",
        }
        self.commands = []  # every ++ command, in order
        self.delivered = []  # (address, bytes) sent to instruments
        self.lines = []  # every raw line received, escapes included
        self.status_byte = 16
        self.terminators = {}  # reply terminator by address, LF unless set
        self.closed = False
        self._line = bytearray()
        self._raw = bytearray()
        self._escaped = False
        self._command = False
        self._tx = bytearray()

    # ---- host side (what pyserial provides)
    @property
    def in_waiting(self):
        return len(self._tx)

    def reset_input_buffer(self):
        self._tx.clear()

    def read(self, size=1):
        if not self._tx:
            time.sleep(self.timeout)
        data = bytes(self._tx[:size])
        del self._tx[:size]
        return data

    def write(self, data):
        for byte in data:
            self._raw.append(byte)
            if self._escaped:
                self._line.append(byte)
                self._escaped = False
            elif byte == 27:
                self._escaped = True
            elif byte in (10, 13):
                self._end_of_line()
            elif byte == 43:
                # the leading "++" makes a command, any other unescaped '+' is
                # discarded, as on the real controller
                if self._line in (b"", b"+"):
                    self._line.append(byte)
                    self._command = len(self._line) == 2
            else:
                self._line.append(byte)
        return len(data)

    def close(self):
        self.closed = True

    # ---- controller side
    def _end_of_line(self):
        line, raw = bytes(self._line), bytes(self._raw)
        self._line.clear()
        self._raw.clear()
        was_command, self._command = self._command, False
        if not line:
            return
        self.lines.append(raw)
        if was_command:
            self._run(line[2:].decode())
        else:
            self._deliver(line)

    def _address(self):
        return int(self.config["addr"].split()[0])

    def _deliver(self, data):
        address = self._address()
        self.delivered.append((address, data))
        device = self.instruments.get(address)
        if device is not None:
            device.write(data.decode())
        if self.config["auto"] == "1":
            self._read(None)

    def _run(self, text):
        name, _, value = text.strip().partition(" ")
        self.commands.append(text.strip())
        if name == "ver":
            self._tx += self.version.encode() + b"\r\n"
        elif name == "read":
            self._read(value.strip())
        elif name == "spoll":
            self._tx += f"{self.status_byte}\r\n".encode()
        elif name in ("clr", "trg", "loc", "ifc"):
            pass
        elif name in self.config:
            self.config[name] = value.strip()

    def _read(self, mode):
        device = self.instruments.get(self._address())
        try:
            reply = device.read()
        except (VisaIOError, AttributeError):
            return  # a real controller times out without sending anything
        data = reply.encode() + self.terminators.get(self._address(), "\n").encode()
        if mode not in (None, "eoi"):
            data = data[: data.index(int(mode)) + 1]
        self._tx += data
        if self.config["eot_enable"] == "1":
            self._tx.append(int(self.config["eot_char"]))


class Gpib:
    """A GPIB instrument that replies only on the n-th time it is read."""

    def __init__(self, reply, on_read):
        self.reply, self.on_read, self.reads = reply, on_read, 0

    def write(self, message):
        pass

    def read(self):
        self.reads += 1
        if self.reads < self.on_read:
            raise VisaIOError(0)
        return self.reply


@pytest.fixture
def bus(monkeypatch):
    """A controller on COM9 with a mock instrument at addresses 5, 7 and 12."""
    instruments = {
        5: MockResource("gpib5"),
        7: MockResource("gpib7"),
        12: MockResource("gpib12"),
    }
    port = FakePrologix(instruments)
    opened = []

    def open_serial(name):
        opened.append(name)
        return port

    monkeypatch.setattr(prologix, "_open_serial", open_serial)
    monkeypatch.setattr(prologix, "_list_ports", lambda: ["COM9", "COM4"])
    monkeypatch.setattr(prologix, "_controllers", {})
    port.opened = opened
    return port


@pytest.fixture
def manager(bus):
    manager = PrologixResourceManager()
    yield manager
    manager.close()


# -------------------------------------------------------------- resource strings
@pytest.mark.parametrize(
    "name, expected",
    [
        ("COM3::12", ("COM3", 12, None)),
        ("COM3::12::INSTR", ("COM3", 12, None)),
        ("/dev/ttyUSB0::5", ("/dev/ttyUSB0", 5, None)),
        ("COM3::9::96", ("COM3", 9, 96)),
        ("COM3::9::0::INSTR", ("COM3", 9, 96)),
        ("com3::0", ("com3", 0, None)),
    ],
)
def test_resource_strings(name, expected):
    assert parse_resource(name) == expected


@pytest.mark.parametrize(
    "name", ["COM3", "12", "COM3::31", "COM3::x", "COM3::5::127", "COM3::5::40", ""]
)
def test_invalid_resource_strings(name):
    with pytest.raises(ValueError):
        parse_resource(name)


# -------------------------------------------------------------- opening
def test_the_adapter_is_registered_by_name():
    assert isinstance(get_adapter("prologix"), PrologixResourceManager)


def test_opening_configures_the_controller_safely(bus, manager):
    manager.open_resource("COM9::5")
    assert bus.commands[0] == "ver"
    assert bus.commands[1] == "savecfg 0"  # before anything is changed
    assert bus.config["savecfg"] == "0"
    assert bus.config["mode"] == "1"
    assert bus.config["auto"] == "0"
    assert bus.config["eos"] == "3"
    assert bus.config["eot_char"] == str(SENTINEL)


def test_a_port_with_no_controller_is_refused_and_released(monkeypatch, bus, manager):
    bus.version = ""
    monkeypatch.setattr(bus, "_run", lambda text: None)
    with pytest.raises(ConnectionError):
        manager.open_resource("COM9::5")
    assert bus.closed
    assert prologix._controllers == {}


def test_something_that_is_not_a_prologix_is_refused(bus, manager):
    bus.version = "Some other device"
    with pytest.raises(ConnectionError):
        manager.open_resource("COM9::5")
    assert bus.closed


def test_unknown_attributes_are_refused(bus, manager):
    with pytest.raises(ValueError):
        manager.open_resource("COM9::5", read_terminaton="\n")
    assert bus.closed  # the port is not left open


def test_visa_only_arguments_are_ignored(bus, manager):
    resource = manager.open_resource(
        "COM9::5", timeout=5000, access_mode=0, open_timeout=1000
    )
    assert resource.timeout == 5000


def test_pyvisa_defaults(bus, manager):
    r = manager.open_resource("COM9::5")
    assert (r.read_termination, r.write_termination) == (None, "\r\n")
    assert (r.send_end, r.encoding, r.timeout, r.query_delay) == (
        True,
        "ascii",
        2000,
        0,
    )


def test_listing_resources(bus):
    resources = PrologixResourceManager().list_resources()
    assert list(resources) == ["COM9", "COM4"]
    assert "COM9::12" in resources
    assert "com9::12::INSTR" in resources
    assert "COM8::12" not in resources
    assert "COM9::31" not in resources
    assert "nonsense" not in resources


def test_experiment_opens_a_resource_through_the_listing(bus):
    resource = Experiment._open_resource(
        get_adapter("prologix"), "COM9::12", timeout=3000
    )
    assert resource is not None
    assert Experiment._open_resource(get_adapter("prologix"), "COM8::12") is None


# -------------------------------------------------------------- writing
def test_write_terminates_like_pyvisa(bus, manager):
    r = manager.open_resource("COM9::5")
    assert r.write("*CLS") == len("*CLS\r\n")
    assert bus.delivered == [(5, b"*CLS\r\n")]


def test_write_termination_is_configurable(bus, manager):
    r = manager.open_resource("COM9::5", write_termination="\n")
    r.write("*CLS")
    r2 = manager.open_resource("COM9::7", write_termination="")
    r2.write("*CLS")
    assert bus.delivered == [(5, b"*CLS\n"), (7, b"*CLS")]


def test_special_characters_are_escaped_so_they_arrive_intact(bus, manager):
    r = manager.open_resource("COM9::5")
    r.write("SOUR:CURR +1.5e+00\x1b")
    assert bus.delivered[-1] == (5, b"SOUR:CURR +1.5e+00\x1b\r\n")
    on_the_wire = bus.lines[-1]
    assert b"\x1b+" in on_the_wire  # every '+' is escaped
    assert on_the_wire.endswith(
        b"\x1b\r\x1b\n\n"
    )  # the terminator is data, not the end of line


def test_writing_a_message_that_begins_with_plus_plus_is_not_a_controller_command(
    bus, manager
):
    r = manager.open_resource("COM9::5")
    r.write("++rst")
    assert bus.delivered[-1] == (5, b"++rst\r\n")
    assert "rst" not in bus.commands


def test_send_end_controls_eoi(bus, manager):
    manager.open_resource("COM9::5", send_end=False).write("X")
    assert bus.config["eoi"] == "0"
    manager.open_resource("COM9::7").write("X")
    assert bus.config["eoi"] == "1"


def test_a_write_does_not_read_back(bus, manager):
    r = manager.open_resource("COM9::5")
    r.write("SOUR:CURR 1e-3")
    assert not any(c.split()[0] == "read" for c in bus.commands)
    assert (
        bus.config["auto"] == "0"
    )  # otherwise every setter would provoke a talk cycle


# -------------------------------------------------------------- reading
def test_query_returns_the_reply_as_pyvisa_does(bus, manager):
    r = manager.open_resource("COM9::5")
    r.write("SOUR:CURR 1e-3")
    assert r.query("SOUR:CURR?") == "1e-3\n"  # no read_termination, so the LF stays
    assert "read eoi" in bus.commands
    assert bus.config["eot_enable"] == "1"


def test_read_termination_is_stripped(bus, manager):
    r = manager.open_resource("COM9::5", read_termination="\n")
    assert r.query("*IDN?") == "MOCK,gpib5,0,0"
    assert "read 10" in bus.commands
    assert bus.config["eot_enable"] == "0"


def test_a_multi_character_read_termination(bus, manager):
    bus.terminators[5] = "\r\n"
    r = manager.open_resource("COM9::5", read_termination="\r\n")
    assert r.query("*IDN?") == "MOCK,gpib5,0,0"
    assert "read 10" in bus.commands  # the controller stops on the last character


def test_no_reply_times_out_like_pyvisa(bus, manager):
    r = manager.open_resource("COM9::5", timeout=150)
    r.write("SOUR:CURR 1e-3")
    started = time.monotonic()
    with pytest.raises(VisaIOError):
        r.read()
    assert 0.1 < time.monotonic() - started < 1.0


def test_the_controllers_timeout_follows_the_resource_timeout(bus, manager):
    manager.open_resource("COM9::5", timeout=1234).write("X")
    assert bus.config["read_tmo_ms"] == "1234"
    manager.open_resource("COM9::7", timeout=60000).write("X")
    assert bus.config["read_tmo_ms"] == "3000"  # the most it accepts
    manager.open_resource("COM9::12", timeout=None).write("X")
    assert bus.config["read_tmo_ms"] == "3000"


def test_a_timeout_longer_than_the_controller_allows_asks_again(
    bus, manager, monkeypatch
):
    monkeypatch.setattr(prologix, "_MAX_READ_TMO_MS", 100)
    bus.instruments[5] = Gpib("late", on_read=3)  # answers the third time it is asked
    r = manager.open_resource("COM9::5", timeout=2000)
    assert r.query("X?") == "late\n"
    assert bus.commands.count("read eoi") == 3


def test_the_retry_gives_up_at_the_timeout(bus, manager, monkeypatch):
    monkeypatch.setattr(prologix, "_MAX_READ_TMO_MS", 100)
    bus.instruments[5] = Gpib("never", on_read=10**6)
    r = manager.open_resource("COM9::5", timeout=500)
    started = time.monotonic()
    with pytest.raises(VisaIOError):
        r.query("X?")
    assert time.monotonic() - started < 1.5


def test_stale_input_does_not_answer_the_next_query(bus, manager):
    r = manager.open_resource("COM9::5")
    bus._tx += b"left over from a timed out read\n\x04"
    r.write("SOUR:CURR 2e-3")
    assert r.query("SOUR:CURR?") == "2e-3\n"


def test_query_delay_is_honoured(bus, manager):
    r = manager.open_resource("COM9::5", query_delay=0.15)
    started = time.monotonic()
    r.query("*IDN?")
    assert time.monotonic() - started >= 0.15


# -------------------------------------------------------------- sharing the bus
def test_instruments_on_one_controller_share_the_port(bus, manager):
    a = manager.open_resource("COM9::5")
    b = manager.open_resource("COM9::7")
    assert bus.opened == ["COM9"]
    a.close()
    assert not bus.closed  # b still needs it
    b.close()
    assert bus.closed
    assert prologix._controllers == {}


def test_the_address_is_only_sent_when_the_bus_switches(bus, manager):
    a = manager.open_resource("COM9::5")
    b = manager.open_resource("COM9::7")
    a.write("X")
    a.write("X")
    b.write("X")
    a.write("X")
    assert [c for c in bus.commands if c.startswith("addr")] == [
        "addr 5",
        "addr 7",
        "addr 5",
    ]
    assert [address for address, _ in bus.delivered] == [5, 5, 7, 5]


def test_each_instrument_gets_its_own_settings_when_the_bus_switches(bus, manager):
    terminated = manager.open_resource("COM9::5", read_termination="\n", timeout=800)
    on_eoi = manager.open_resource("COM9::7", timeout=1500)
    for _ in range(2):
        assert terminated.query("*IDN?") == "MOCK,gpib5,0,0"
        assert on_eoi.query("*IDN?") == "MOCK,gpib7,0,0\n"


def test_a_secondary_address(bus, manager):
    manager.open_resource("COM9::9::0").write("X")
    assert bus.config["addr"] == "9 96"


def test_closed_resources_refuse_io(bus, manager):
    r = manager.open_resource("COM9::5")
    r.close()
    r.close()  # closing twice is harmless
    for call in (r.read, lambda: r.write("X"), lambda: r.query("X?"), r.clear):
        with pytest.raises(InvalidSession):
            call()


def test_context_manager(bus, manager):
    with manager.open_resource("COM9::5") as r:
        assert r.opened
    assert not r.opened and bus.closed


def test_replies_are_never_crossed_between_threads(bus, manager):
    resources = {
        5: manager.open_resource("COM9::5", read_termination="\n"),
        7: manager.open_resource("COM9::7", read_termination="\n"),
        12: manager.open_resource("COM9::12"),
    }
    failures = []

    def hammer(address):
        r = resources[address]
        for i in range(25):
            r.write(f"SOUR:CURR {i}e-3")
            reply = r.query("SOUR:CURR?").strip()
            if reply != f"{i}e-3":
                failures.append((address, i, reply))

    threads = [threading.Thread(target=hammer, args=(a,)) for a in resources]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert failures == []


# -------------------------------------------------------------- controller commands
def test_clear_trigger_and_serial_poll(bus, manager):
    r = manager.open_resource("COM9::7")
    r.clear()
    r.assert_trigger()
    assert r.read_stb() == 16
    assert bus.commands[-3:] == ["clr", "trg", "spoll"]
    assert bus.config["addr"] == "7"


# -------------------------------------------------------------- with instruments
def test_a_hardware_instrument_works_behind_the_controller(bus, manager):
    k = Keithley_6221("k", manager.open_resource("COM9::12", read_termination="\n"))

    k.set_current(1.5e-6)  # sent as 1.500000e-06: the '+' and '-' signs must survive
    k.set_wave_amplitude(2e-3)
    k.set_output_state(State.ON)

    assert k.get_current() == pytest.approx(1.5e-6)
    assert k.get_wave_amplitude() == pytest.approx(2e-3)
    assert k.get_output_state() is State.ON
    assert k.identify() == "MOCK,gpib12,0,0"


def test_an_instrument_without_read_termination_still_parses(bus, manager):
    k = Keithley_6221("k", manager.open_resource("COM9::12"))
    k.set_current(3e-3)
    assert k.get_current() == pytest.approx(3e-3)  # "3.000000e-03\n" still converts


def test_two_instruments_from_a_config_share_one_controller(bus, tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    config = {
        "instruments": {
            "current": {
                "instrument": "Keithley_6221",
                "adapter": "prologix",
                "resource": "COM9::12",
                "args": {"read_termination": "\n"},
            },
            "temperature": {
                "instrument": "Lakeshore_350",
                "adapter": "prologix",
                "resource": "COM9::5",
                "args": {"read_termination": "\r\n"},
            },
        }
    }
    bus.terminators[5] = "\r\n"

    Experiment._configure_instruments(experiment, config)

    assert set(experiment.instruments) == {"current", "temperature"}
    assert bus.opened == ["COM9"]  # both instruments, one open port
    lake = experiment.instruments["temperature"]
    assert isinstance(lake, Lakeshore_350)
    lake.set_setpoint(OutputChannel.OUTPUT_1, 4.2)
    assert lake.get_setpoint(OutputChannel.OUTPUT_1) == pytest.approx(4.2)
    assert experiment.instruments["current"].identify() == "MOCK,gpib12,0,0"
