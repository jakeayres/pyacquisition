"""Enum arguments can be given as text, and the enums can be reached from the instrument."""

import inspect
import typing
from enum import Enum
from functools import partial

import pytest

from pyacquisition import Experiment, Measurement
from pyacquisition.core.instrument import BaseEnum, resolve_enum_kwargs
from pyacquisition.instruments import (
    Lakeshore_340,
    Lakeshore_350,
    instrument_map,
)
from pyacquisition.instruments.lakeshore import lakeshore_340, lakeshore_350


class Channel(BaseEnum):
    INPUT_A = ("A", "Input A")
    INPUT_B = ("B", "Input B")


class Other(BaseEnum):
    OUTPUT_1 = (1, "Output 1")
    OUTPUT_2 = (2, "Output 2")


class Plain(Enum):
    RED = 1
    BLUE = 2


def read(channel: Channel, scale: float = 1.0, name: str = "x"):
    return channel


def read_either(channel: Channel | Other):
    return channel


def read_or_text(channel: Channel | str):
    return channel


def read_plain(colour: Plain):
    return colour


# ------------------------------------------------------------ the resolver
@pytest.mark.parametrize(
    "text",
    ["INPUT_A", "Input A", "input a", "input_a", "INPUT A", "input-a", " Input A "],
)
def test_text_names_a_member_by_name_or_label_in_any_case(text):
    assert resolve_enum_kwargs(read, {"channel": text}) == {"channel": Channel.INPUT_A}


def test_members_and_other_values_pass_through_unchanged():
    given = {"channel": Channel.INPUT_B, "scale": 2.5, "name": "INPUT_A"}
    assert resolve_enum_kwargs(read, given) == given  # "name" is a str, not an enum


def test_the_original_dict_is_not_changed():
    given = {"channel": "INPUT_A"}
    resolve_enum_kwargs(read, given)
    assert given == {"channel": "INPUT_A"}


def test_a_name_that_matches_nothing_says_what_would():
    with pytest.raises(ValueError) as error:
        resolve_enum_kwargs(read, {"channel": "INPUT_Z"})
    message = str(error.value)
    assert "`channel`" in message and "'INPUT_Z'" in message
    assert "INPUT_A, INPUT_B" in message


def test_the_exact_name_wins_over_a_looser_match():
    class Tricky(BaseEnum):
        A = (1, "b")
        B = (2, "a")

    def function(x: Tricky):
        return x

    # "A" is the name of one member and the label of another, and the name wins
    assert resolve_enum_kwargs(function, {"x": "A"}) == {"x": Tricky.A}


def test_a_name_that_could_mean_two_members_is_refused():
    class Twins(BaseEnum):
        ONE = (1, "Same")
        TWO = (2, "same")

    def function(x: Twins):
        return x

    with pytest.raises(ValueError, match="could mean"):
        resolve_enum_kwargs(function, {"x": "SAME"})


def test_enums_that_are_copies_of_one_another_are_not_ambiguous():
    class Copy(BaseEnum):
        INPUT_A = ("A", "Input A")
        INPUT_B = ("B", "Input B")

    def function(channel: Channel | Copy):
        return channel

    # the same names in both, so any way of saying it has one answer
    assert resolve_enum_kwargs(function, {"channel": "input a"})["channel"].name == (
        "INPUT_A"
    )


def test_a_union_of_enums_takes_a_member_of_any_of_them():
    assert resolve_enum_kwargs(read_either, {"channel": "OUTPUT_2"}) == {
        "channel": Other.OUTPUT_2
    }
    assert resolve_enum_kwargs(read_either, {"channel": "Input B"}) == {
        "channel": Channel.INPUT_B
    }


def test_text_that_the_annotation_allows_is_kept_when_it_names_nothing():
    assert resolve_enum_kwargs(read_or_text, {"channel": "anything"}) == {
        "channel": "anything"
    }
    assert resolve_enum_kwargs(read_or_text, {"channel": "INPUT_A"}) == {
        "channel": Channel.INPUT_A
    }


def test_a_plain_enum_is_named_by_its_name():
    assert resolve_enum_kwargs(read_plain, {"colour": "blue"}) == {"colour": Plain.BLUE}


def test_a_partial_is_resolved_too():
    function = partial(read, scale=2.0)
    assert resolve_enum_kwargs(function, {"channel": "INPUT_B"}) == {
        "channel": Channel.INPUT_B
    }


def test_a_bound_method_is_resolved():
    from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel

    method = Lakeshore_350("ls", "x", adapter="mock").get_temperature
    assert resolve_enum_kwargs(method, {"input_channel": "input_b"}) == {
        "input_channel": InputChannel.INPUT_B
    }


def test_an_argument_the_function_does_not_take_is_left_for_the_caller_to_report():
    assert resolve_enum_kwargs(read, {"nonsense": "INPUT_A"}) == {"nonsense": "INPUT_A"}


# ---------------------------------------------------------- measurements
@pytest.fixture
def cryo():
    return Lakeshore_350(
        "ls",
        "GPIB0::12::INSTR",
        adapter="mock",
        responses={"KRDG? A": "4.2", "KRDG? B": "77.0"},
    )


def test_a_measurement_takes_the_name_of_a_member(cryo):
    measurement = Measurement("T", cryo.get_temperature, input_channel="INPUT_A")
    assert measurement.run() == pytest.approx(4.2)


def test_a_measurement_takes_the_label_in_any_case(cryo):
    measurement = Measurement("T", cryo.get_temperature, input_channel="input b")
    assert measurement.run() == pytest.approx(77.0)


def test_a_measurement_still_takes_a_member(cryo):
    from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel

    measurement = Measurement(
        "T", cryo.get_temperature, input_channel=InputChannel.INPUT_A
    )
    assert measurement.run() == pytest.approx(4.2)


def test_a_mistake_in_the_name_stops_the_measurement_being_made(cryo):
    with pytest.raises(ValueError, match="INPUT_A, INPUT_B, INPUT_C, INPUT_D"):
        Measurement("T", cryo.get_temperature, input_channel="INPUT_Z")


def test_a_wrong_keyword_is_still_refused(cryo):
    with pytest.raises(ValueError, match="Invalid keyword argument"):
        Measurement("T", cryo.get_temperature, channel="INPUT_A")


# ------------------------------------------------------------- from a config
def test_a_config_takes_a_label_in_any_case(cryo):
    from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel

    method = Experiment._resolve_method_args(
        cryo.get_temperature, {"input_channel": "input a"}
    )
    assert method.keywords == {"input_channel": InputChannel.INPUT_A}


def test_a_config_still_takes_the_name(cryo):
    method = Experiment._resolve_method_args(
        cryo.get_temperature, {"input_channel": "INPUT_B"}
    )
    assert method() == pytest.approx(77.0)


def test_a_config_with_a_bad_name_or_a_number_for_an_enum_is_refused(cryo):
    with pytest.raises(ValueError, match="INPUT_A"):
        Experiment._resolve_method_args(cryo.get_temperature, {"input_channel": "Z"})
    with pytest.raises(ValueError, match="must name a member"):
        Experiment._resolve_method_args(cryo.get_temperature, {"input_channel": 3})


def test_a_config_leaves_other_arguments_alone(cryo):
    method = Experiment._resolve_method_args(
        cryo.get_temperature, {"input_channel": "INPUT_A", "not_an_argument": 1}
    )
    assert set(method.keywords) == {"input_channel"}


# ------------------------------------------------ the enums on the instrument
def enums_in(annotation):
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return [annotation]
    found = []
    for argument in typing.get_args(annotation):
        found += enums_in(argument)
    return found


@pytest.mark.parametrize("name", sorted(instrument_map))
def test_every_enum_that_an_instrument_takes_is_reachable_from_it(name):
    cls = instrument_map[name]
    wanted = {}
    for function in [*cls._queries, *cls._commands]:
        for hint in typing.get_type_hints(function).values():
            for enum in enums_in(hint):
                wanted[enum.__name__] = enum

    for enum_name, enum in wanted.items():
        assert getattr(cls, enum_name, None) is enum, (
            f"{name}.{enum_name} is missing or is a different enum"
        )


def test_the_enums_are_the_ones_in_the_instruments_module():
    assert Lakeshore_350.InputChannel is lakeshore_350.InputChannel
    assert Lakeshore_350.OutputChannel is lakeshore_350.OutputChannel
    assert Lakeshore_340.InputChannel is lakeshore_340.InputChannel


def test_the_two_lakeshores_keep_their_own_enums():
    # Different classes with the same name, which is why they are not one import
    assert Lakeshore_340.InputChannel is not Lakeshore_350.InputChannel


def test_the_enums_can_be_used_from_the_instrument_without_an_import(cryo):
    measurement = Measurement(
        "T", cryo.get_temperature, input_channel=cryo.InputChannel.INPUT_B
    )
    assert measurement.run() == pytest.approx(77.0)
    assert cryo.set_setpoint(Lakeshore_350.OutputChannel.OUTPUT_1, 5.0) is not None


def test_exposing_the_enums_does_not_add_queries_or_commands():
    assert "InputChannel" not in {q.__name__ for q in Lakeshore_350._queries}
    assert "InputChannel" not in {c.__name__ for c in Lakeshore_350._commands}
