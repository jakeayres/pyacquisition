"""A small instrument, and a bench to run it on, for testing the verification engine."""

import tomllib

from pyacquisition.core.adapters.mock import MockResource
from pyacquisition.core.instrument import (
    BaseEnum,
    Instrument,
    mark_command,
    mark_query,
)
from pyacquisition.verify import (
    Hazard,
    Policy,
    build_session,
    parse_spec,
    plan,
)
from pyacquisition.verify.inventory import Entry
from pyacquisition.verify.spec import validate


class State(BaseEnum):
    OFF = (0, "Off")
    ON = (1, "On")


class Mode(BaseEnum):
    A = ("a", "Mode A")
    B = ("b", "Mode B")
    C = ("c", "Mode C")


class Channel(BaseEnum):
    ONE = (1, "One")
    TWO = (2, "Two")


class FakeInstrument(Instrument):
    """Well behaved, apart from `set_target`, which is registered as a query as
    `Mercury_IPS` registers its setters."""

    def __init__(self, uid, visa_resource):
        super().__init__(uid, visa_resource)
        self.command("INIT")

    @mark_query
    def identify(self) -> str:
        return self.query("*IDN?")

    @mark_query
    def get_level(self) -> float:
        return float(self.query("LEVEL?"))

    @mark_command
    def set_level(self, level: float) -> int:
        if level == 99.0:
            raise RuntimeError("the setter blew up")
        return self.command(f"LEVEL {level}")

    @mark_query
    def get_mode(self) -> Mode:
        return Mode.from_raw_value(self.query("MODE?"))

    @mark_command
    def set_mode(self, mode: Mode) -> int:
        return self.command(f"MODE {mode.raw_value}")

    @mark_query
    def get_gain(self, channel: Channel) -> float:
        return float(self.query(f"GAIN? {channel.raw_value}"))

    @mark_command
    def set_gain(self, channel: Channel, gain: float) -> int:
        return self.command(f"GAIN {channel.raw_value},{gain}")

    @mark_query
    def get_count(self, index: int) -> int:
        return int(self.query(f"COUNT? {index}"))

    @mark_query
    def get_output_state(self) -> State:
        return State.from_raw_value(int(self.query("OUT?")))

    @mark_command
    def set_output_state(self, state: State) -> int:
        return self.command(f"OUT {state.raw_value}")

    @mark_query
    def set_target(self, x: float) -> int:  # an action, registered as a query
        return self.query(f"J{x}")

    @mark_query
    def hold(self) -> int:  # an action, registered as a query
        return self.query("A0")

    @mark_command
    def reset(self) -> int:
        return self.command("*RST")


class MisbehavingInstrument(FakeInstrument):
    @mark_query
    def get_bad(self) -> float:
        return float(self.query("BAD?"))

    @mark_query
    def get_sneaky(self) -> float:
        self.command("BOOM")  # a getter that writes
        return 0.0


IDENTITY = "ACME,FAKE-100,1"

SEED = {
    "LEVEL": "3.0",
    "MODE": "a",
    "OUT": "0",
    "GAIN 1": "1.5",
    "GAIN 2": "2.5",
}

BASE_SPEC = """
[identity]
contains = ["ACME", "FAKE"]

[safe_state]
steps = [{ call = "set_output_state", args = { state = "OFF" } }]
verify = [{ call = "get_output_state", equals = "OFF" }]

[read.get_count]
args = [{ index = 1 }]

[roundtrip.level]
hazard = "reversible"
values = [1.0, 2.0]

[roundtrip.mode]
hazard = "reversible"
values = "*"

[roundtrip.gain]
hazard = "reversible"
values = [0.5]
select = { channel = "*" }

[roundtrip.output_state]
hazard = "hazardous"
values = "*"
"""


def make_spec(text=BASE_SPEC, cls=FakeInstrument):
    spec = parse_spec(tomllib.loads(text), "test")
    validate(spec, cls)
    return spec


def make_resource(seed=None, identity=IDENTITY):
    resource = MockResource("fake", responses={"*IDN?": identity})
    resource.state.update(SEED if seed is None else seed)
    return resource


def make_session(
    text=BASE_SPEC,
    *,
    cls=FakeInstrument,
    limit=Hazard.READ_ONLY,
    max_hazard=None,
    resource=None,
    capabilities=(),
    skip=(),
    dry_run=False,
):
    """Returns the session, its resource and the spec it was built with."""
    spec = make_spec(text, cls) if text is not None else None
    resource = resource or make_resource()
    entry = Entry(
        name="fake",
        cls=cls,
        adapter=None,
        resource=None,
        max_hazard=max_hazard,
        capabilities=tuple(capabilities),
        skip=tuple(skip),
    )
    session = build_session(entry, resource, Policy(limit), dry_run=dry_run, spec=spec)
    return session, resource, spec


def run_all(session, cls=FakeInstrument, spec=None):
    """Runs the whole plan, returning the results by check id."""
    return {r.check: r for r in (session.run(c) for c in plan(cls, spec))}
