"""Method groups: `@mark_query(group=...)` and `@mark_command(group=...)` sort a
driver's methods into the parts of the instrument they belong to, and
`method_groups` gives them in the order of the code. The docs read the same
groups from the source (templates/python/material/_groups.html.jinja), so the
two are checked against each other."""

from pathlib import Path

import griffe
import jinja2
import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment
from pyacquisition.core.instrument import (
    GROUP_KEY,
    ORDER_KEY,
    OTHER_GROUP,
    SoftwareInstrument,
    mark_command,
    mark_query,
    method_groups,
)
from pyacquisition.instruments import (
    SR_830,
    SR_860,
    Keithley_2000,
    Keithley_6221,
    Lakeshore_340,
    Lakeshore_350,
    Mercury_IPS,
    PIDController,
    RandomNumberGenerator,
    instrument_map,
)

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates" / "python" / "material"

# The drivers whose every query and command of their own has a group. The other
# software instruments, with eight or fewer, are left flat.
GROUPED = [
    Keithley_2000,
    Keithley_6221,
    Lakeshore_340,
    Lakeshore_350,
    Mercury_IPS,
    SR_830,
    SR_860,
    PIDController,
    RandomNumberGenerator,
]

# Every driver that comes with PyAcquisition: those a config can name, and the
# PID task's, which is made in code.
DRIVERS = {**instrument_map, "PIDController": PIDController}


class Grouped(SoftwareInstrument):
    @mark_query(group="Inputs")
    def get_level(self) -> float:
        return 1.0

    @mark_command
    def beep(self) -> None:
        pass

    @mark_command(group="Outputs")
    def set_output(self, value: float) -> None:
        pass

    @mark_command(group="Inputs")
    def set_level(self, value: float) -> None:
        pass

    def helper(self):
        """Not a query or a command, so in no group."""


class Plain(SoftwareInstrument):
    @mark_query
    def get_level(self) -> float:
        return 1.0

    @mark_command
    def set_level(self, value: float) -> None:
        pass


def test_a_bare_marker_works_as_it_always_has():
    assert Plain.get_level._is_query and Plain.set_level._is_command
    assert Plain.get_level._group is None
    assert {q.__name__ for q in Plain._queries} == {"get_level"}
    assert {c.__name__ for c in Plain._commands} == {"set_level"}


def test_a_marker_called_with_a_group_marks_the_method_and_keeps_it():
    assert Grouped.get_level._is_query
    assert Grouped.get_level._group == "Inputs"
    assert Grouped.set_output._is_command
    assert Grouped(uid="g").get_level() == 1.0


def test_a_marker_called_as_a_function_still_marks():
    def get_x(self):
        return 2

    assert mark_query(get_x) is get_x and get_x._is_query


@pytest.mark.parametrize("group", ["", "  ", 3, ["Inputs"]])
def test_a_group_must_be_a_name(group):
    with pytest.raises(TypeError, match="A group is a name"):
        mark_query(group=group)


def test_a_group_given_without_its_name_is_refused():
    with pytest.raises(TypeError, match="group="):
        mark_command("Inputs")


def test_groups_come_in_the_order_of_the_code_with_other_last():
    assert method_groups(Grouped) == {
        "Inputs": ["get_level", "set_level"],
        "Outputs": ["set_output"],
        OTHER_GROUP: ["beep", "identify"],
    }


def test_an_instrument_gives_its_drivers_groups():
    assert method_groups(Grouped(uid="g")) == method_groups(Grouped)


def test_a_driver_with_no_groups_has_none():
    assert method_groups(Plain) == {}


def test_a_subclass_inherits_groups_and_its_own_methods_hide_its_bases():
    class Child(Grouped):
        @mark_query(group="Outputs")
        def get_level(self) -> float:
            return 2.0

        def beep(self):
            """No longer a command."""

    assert method_groups(Child) == {
        "Outputs": ["get_level", "set_output"],
        "Inputs": ["set_level"],
        OTHER_GROUP: ["identify"],
    }


def test_a_query_that_is_a_property_has_its_group():
    class WithProperty(SoftwareInstrument):
        @property
        @mark_query(group="Inputs")
        def level(self) -> float:
            return 1.0

    assert method_groups(WithProperty) == {"Inputs": ["level"], OTHER_GROUP: ["identify"]}


@pytest.mark.parametrize("driver", GROUPED, ids=lambda d: d.__name__)
def test_every_query_and_command_of_a_grouped_driver_has_a_group(driver):
    # Only what the driver inherits may be left in Other: a software
    # instrument's identify, from SoftwareInstrument.
    other = method_groups(driver).get(OTHER_GROUP, [])
    assert [name for name in other if name in vars(driver)] == []


def test_the_other_drivers_have_no_groups():
    flat = [driver for driver in DRIVERS.values() if driver not in GROUPED]
    assert flat and all(method_groups(driver) == {} for driver in flat)


# --- the API -----------------------------------------------------------------


def schema(tmp_path, *instruments) -> dict:
    """The API's schema, by path, for an experiment with these instruments."""
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    for instrument in instruments:
        experiment.add_instrument(instrument)
    experiment._rack._register_endpoints(experiment._api_server)
    return TestClient(experiment._api_server.app).get("/openapi.json").json()["paths"]


def placed(paths, uid) -> dict:
    """Each of an instrument's methods' group and place, as the schema gives them."""
    return {
        path.removeprefix(f"/{uid}/"): (route["get"][GROUP_KEY], route["get"][ORDER_KEY])
        for path, route in paths.items()
        if path.startswith(f"/{uid}/") and GROUP_KEY in route["get"]
    }


def test_the_schema_gives_each_method_its_group_and_place_in_the_driver(tmp_path):
    paths = schema(tmp_path, Grouped("g"))
    assert placed(paths, "g") == {
        "get_level": ("Inputs", 0),
        "set_level": ("Inputs", 1),
        "set_output": ("Outputs", 2),
        "beep": (OTHER_GROUP, 3),
        "identify": (OTHER_GROUP, 4),
    }


def test_the_schema_gives_an_ungrouped_driver_nothing_new(tmp_path):
    paths = schema(tmp_path, Plain("p"))
    routes = [route["get"] for path, route in paths.items() if path.startswith("/p/")]
    assert routes and not any(GROUP_KEY in r or ORDER_KEY in r for r in routes)


def test_a_hardware_driver_gives_its_groups_in_the_schema(tmp_path):
    paths = schema(tmp_path, Lakeshore_350("cryo", "GPIB0::12::INSTR", adapter="mock"))
    places = placed(paths, "cryo")
    expected = [name for names in method_groups(Lakeshore_350).values() for name in names]
    assert sorted(places, key=lambda name: places[name][1]) == expected
    assert places["get_heater_range"][0] == "Control loops"


# --- the docs ----------------------------------------------------------------


@pytest.fixture(scope="module")
def macros():
    """The docs' own macros, which read a method's group from its marker."""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES))
    return env.get_template("_groups.html.jinja").module


@pytest.fixture(scope="module")
def package():
    """The package as the docs see it: read from the source, not imported."""
    return griffe.load("pyacquisition", search_paths=[str(ROOT / "src")])


def documented_groups(macros, package, driver) -> dict:
    """A driver's groups as its page in the docs lists them."""
    cls = package[f"{driver.__module__.removeprefix('pyacquisition.')}.{driver.__name__}"]
    marked = sorted(
        (
            f
            for f in cls.functions.values()
            # The page shows the driver's own methods (inherited_members is off).
            if not f.inherited
            and any(d.callable_path.split(".")[-1] in ("mark_query", "mark_command") for d in f.decorators)
        ),
        key=lambda f: f.lineno,
    )
    names = str(macros.group_names(marked)).strip()
    return {
        group: [f.name for f in marked if str(macros.in_group(f, group)) == "yes"]
        for group in (names.split("\n") if names else [])
    }


@pytest.mark.parametrize("name", sorted(DRIVERS))
def test_the_docs_list_a_drivers_methods_in_the_groups_its_code_has(macros, package, name):
    driver = DRIVERS[name]
    expected = method_groups(driver)
    # Inherited methods (`identify` on a software instrument) aren't on the
    # driver's page, which shows only its own.
    own = {
        group: [m for m in methods if m in vars(driver)]
        for group, methods in expected.items()
    }
    own = {group: methods for group, methods in own.items() if methods}
    if list(own) == [OTHER_GROUP]:
        own = {}
    assert documented_groups(macros, package, driver) == own


@pytest.mark.parametrize(
    "group, anchor",
    [
        ("Control loops", "control-loops"),
        ("Relays and digital I/O", "relays-and-digital-i-o"),
        ("  Front panel ", "front-panel"),
    ],
)
def test_a_groups_anchor_is_the_words_of_its_name_in_lower_case(macros, group, anchor):
    assert str(macros.group_id(group)) == anchor
