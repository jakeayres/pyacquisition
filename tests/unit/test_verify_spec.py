import tomllib

import pytest
from fake_instrument import (
    BASE_SPEC,
    Channel,
    FakeInstrument,
    Mode,
    State,
    make_spec,
)

from pyacquisition.verify import Hazard, SpecError, load_spec, parse_spec
from pyacquisition.verify.spec import (
    bind,
    canned,
    check_type,
    coerce,
    roundtrip_shape,
    same,
    spec_path,
)


def parse(text):
    return parse_spec(tomllib.loads(text), "test")


def rejects(text, match, cls=FakeInstrument):
    """The spec must be refused, at parsing or when checked against the class."""
    with pytest.raises(SpecError, match=match):
        make_spec(text, cls)


# ------------------------------------------------------------ parsing
def test_a_full_spec_parses():
    spec = parse(BASE_SPEC)
    assert spec.identity == ("ACME", "FAKE")
    assert spec.steps[0].call == "set_output_state"
    assert spec.verify[0].equals == "OFF"
    assert set(spec.roundtrips) == {"level", "mode", "gain", "output_state"}
    assert spec.roundtrips["output_state"].hazard is Hazard.HAZARDOUS
    assert spec.roundtrips["level"].setter == "set_level"  # by convention
    assert spec.read["get_count"].args == ({"index": 1},)


def test_an_empty_spec_is_valid_and_declares_nothing():
    spec = parse("")
    assert spec.identity is None and spec.steps is None and not spec.roundtrips


def test_a_missing_safe_state_is_not_the_same_as_an_empty_one():
    assert parse("").steps is None
    assert parse("[safe_state]").steps == ()  # "nothing to do", said deliberately


@pytest.mark.parametrize(
    "text, match",
    [
        ("[idnetity]\ncontains = ['A']", "unknown key"),  # a typo at the top
        ("[identity]\ncontain = ['A']", "unknown key"),
        ("[identity]\ncontains = []", "empty"),
        ("[guard]\nread = ['(']", "bad pattern"),
        ("[safe_state]\nstep = []", "unknown key"),
        ("[safe_state]\nsteps = [{ call = 'x', equals = 1 }]", "unknown key"),
        ("[safe_state]\nverify = [{ call = 'get_x' }]", "'equals' is required"),
        ("[read.get_x]\nskp = 'why'", "unknown key"),
        ("[read.get_x]\nhazard = 'safe'", "unknown hazard"),
        ("[read.get_x]\nrange = [1]", "range"),
        ("[read.get_x]\nargs = 3", "args"),
    ],
)
def test_typos_and_nonsense_are_errors_not_defaults(text, match):
    with pytest.raises(SpecError, match=match):
        parse(text)


@pytest.mark.parametrize(
    "body, match",
    [
        ("values = [1.0]", "'hazard' is required"),  # every write is tagged
        ("hazard = 'read-only'\nvalues = [1.0]", "cannot be read-only"),
        ("hazard = 'reversible'", "'values' must be"),
        ("hazard = 'reversible'\nvalues = []", "'values' must be"),
        ("hazard = 'reversible'\nvalues = [1.0]\nhazrd = 'x'", "unknown key"),
        ("hazard = 'sortof'\nvalues = [1.0]", "unknown hazard"),
        ("hazard = 'reversible'\nvalues = [1.0]\nselect = { a = [] }", "select.a"),
    ],
)
def test_a_round_trip_must_say_what_it_does(body, match):
    with pytest.raises(SpecError, match=match):
        parse(f"[roundtrip.level]\n{body}")


# ------------------------------------------------------------ against the class
def test_a_spec_beside_no_class_file_is_none():
    assert not spec_path(FakeInstrument).exists()
    assert load_spec(FakeInstrument) is None


@pytest.mark.parametrize(
    "text, match",
    [
        ("[read.get_nothing]\nskip = 'x'", "no method 'get_nothing'"),
        ("[read.set_level]\nskip = 'x'", "only getters"),
        ("[read.get_count]\nargs = [{ idx = 1 }]", "no parameter"),
        ("[read.get_count]\nargs = [{ index = 1.5 }]", "whole number"),
        ("[safe_state]\nsteps = [{ call = 'nope' }]", "no method 'nope'"),
        (
            "[safe_state]\nsteps = [{ call = 'set_output_state' }]",
            "missing",
        ),
        (
            "[safe_state]\nsteps = [{ call = 'set_output_state', args = { state = 'SIDEWAYS' } }]",
            "not one of",
        ),
        (
            "[safe_state]\nverify = [{ call = 'set_level', equals = 1 }]",
            "must call a getter",
        ),
    ],
)
def test_the_spec_must_fit_the_class(text, match):
    rejects(text, match)


@pytest.mark.parametrize(
    "body, match",
    [
        ("setter = 'set_nothing'\nvalues = [1.0]", "no method 'set_nothing'"),
        ("getter = 'get_nothing'\nvalues = [1.0]", "no method 'get_nothing'"),
        ("getter = 'set_level'\nvalues = [1.0]", "must be named get_"),
        ("values = ['x']", "not a number|could not convert"),
        ("values = '*'", "only works for enum"),
        ("param = 'nope'\nvalues = [1.0]", "no parameter 'nope'"),
        ("select = { channel = ['ONE'] }\nvalues = [1.0]", "not parameters"),
    ],
)
def test_a_round_trip_must_fit_its_setter_and_getter(body, match):
    rejects(f"[roundtrip.level]\nhazard = 'reversible'\n{body}", match)


def test_a_round_trip_cannot_restore_what_the_getter_cannot_return():
    # set_level takes a float, get_mode returns an enum: nothing to give back
    rejects(
        "[roundtrip.level]\nhazard = 'reversible'\ngetter = 'get_mode'\nvalues = [1.0]",
        "could not be restored",
    )


def test_every_parameter_of_the_setter_and_getter_must_be_covered():
    rejects(
        "[roundtrip.gain]\nhazard = 'reversible'\nvalues = [1.0]",
        "also needs|takes",
    )
    rejects(
        "[roundtrip.gain]\nhazard = 'reversible'\nvalues = [1.0]\n"
        "select = { channel = ['THREE'] }",
        "not one of",
    )


def test_a_precondition_is_checked_like_everything_else():
    rejects(
        "[roundtrip.level]\nhazard = 'reversible'\nvalues = [1.0]\n"
        "preconditions = [{ call = 'get_output_state', equals = 'HALF' }]",
        "not one of",
    )


def test_all_the_problems_are_reported_together():
    with pytest.raises(SpecError) as error:
        make_spec("[read.get_a]\nskip = 'x'\n[read.get_b]\nskip = 'x'")
    assert "2 problem" in str(error.value)


def test_roundtrip_shape_expands_enums_and_combinations():
    spec = make_spec()
    param, values, selects = roundtrip_shape(spec.roundtrips["gain"], FakeInstrument)
    assert (param, values) == ("gain", [0.5])
    assert selects == [{"channel": Channel.ONE}, {"channel": Channel.TWO}]
    _, values, selects = roundtrip_shape(spec.roundtrips["mode"], FakeInstrument)
    assert values == [Mode.A, Mode.B, Mode.C] and selects == [{}]


# ------------------------------------------------------------ helpers
def test_coerce_turns_names_into_members_and_checks_types():
    assert coerce("ON", State) is State.ON
    assert coerce(State.OFF, State) is State.OFF
    assert coerce(3, float) == 3.0 and isinstance(coerce(3, float), float)
    assert coerce(2.0, int) == 2
    assert coerce([1, 2], list[float]) == [1.0, 2.0]
    with pytest.raises(SpecError, match="whole number"):
        coerce(2.5, int)
    with pytest.raises(SpecError, match="not true or false"):
        coerce(1, bool)
    with pytest.raises(SpecError, match="not one of"):
        coerce("MAYBE", State)


def test_bind_names_the_offending_parameter():
    func = FakeInstrument.set_gain
    assert bind(func, {"channel": "ONE", "gain": 2}, "x") == {
        "channel": Channel.ONE,
        "gain": 2.0,
    }
    with pytest.raises(SpecError, match="no parameter"):
        bind(func, {"channel": "ONE", "gain": 2, "extra": 1}, "x")
    with pytest.raises(SpecError, match="missing"):
        bind(func, {"channel": "ONE"}, "x")


def test_same_compares_numbers_with_tolerance_and_the_rest_exactly():
    assert same(1.0000001, 1.0, rel=1e-6)
    assert not same(1.1, 1.0, rel=1e-6)
    assert same(0.0000001, 0.0, abs_tol=1e-6)
    assert same(State.ON, State.ON) and not same(State.ON, State.OFF)
    assert not same(True, 1.5)
    assert same(float("inf"), float("inf"))


def test_check_type():
    assert check_type(1.5, float) is None
    assert check_type(1, float) is None  # an int is a fine float
    assert check_type(True, float) is not None
    assert check_type(True, int) is not None
    assert check_type("x", float) is not None
    assert check_type(State.ON, State) is None
    assert check_type(Mode.A, State) is not None
    assert check_type([1.0], list[float]) is None
    assert check_type({}, dict) is None
    assert check_type(object(), None) is None


def test_canned_values_have_the_right_type():
    assert canned(State) is State.OFF
    assert canned(float) == 0.0 and canned(int) == 0 and canned(str) == ""
    assert canned(bool) is False and canned(list[float]) == []
    assert canned(None) is None


def test_generic_annotations_are_compatible_when_equal():
    from pyacquisition.verify.spec import compatible

    assert compatible(list[int], list[int])
    assert not compatible(list[int], list[float])
    assert not compatible(list[int], int)
    assert compatible(State, State) and not compatible(State, Mode)
    assert compatible(int, float) and not compatible(str, float)
