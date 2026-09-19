"""Helpers and enums shared by the Keithley SCPI instruments."""

import math
import re

from ...core.instrument import BaseEnum


def format_number(value: float) -> str:
    """Formats a number in scientific notation.

    Fixed decimals would truncate the small values instruments accept.
    """
    return f"{value:.6e}"


def format_count(value: float) -> str:
    """Formats a count, where infinity is sent as INF."""
    return "INF" if math.isinf(value) else str(int(value))


def format_duration(value: float) -> str:
    """Formats a duration, where infinity is sent as INF."""
    return "INF" if math.isinf(value) else format_number(value)


def format_list(values: list[float]) -> str:
    """Formats numbers as a comma separated list."""
    return ",".join(format_number(value) for value in values)


def to_int(reply: str) -> int:
    """Converts a reply that may be formatted as an integer or in scientific notation."""
    return int(float(reply))


def to_floats(reply: str) -> list[float]:
    """Converts a comma separated reply to numbers."""
    return [float(item) for item in reply.split(",") if item.strip()]


def to_ints(reply: str) -> list[int]:
    """Converts a comma separated reply to whole numbers."""
    return [to_int(item) for item in reply.split(",") if item.strip()]


def unquote(reply: str) -> str:
    """Strips whitespace and surrounding quotes from a string reply."""
    return reply.strip().strip("\"'")


_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def first_number(reply: str) -> float:
    """Reads the leading number of a reading string, ignoring any units suffix."""
    match = _NUMBER.match(reply.strip())
    if match is None:
        raise ValueError(f"No reading found in reply: {reply!r}")
    return float(match.group())


def parse_enum(enum_cls, reply: str):
    """Finds the enum member for a reply, accepting the short or long form of a name."""
    text = unquote(reply).upper()
    matches = [m for m in enum_cls if text.startswith(str(m.raw_value).upper())]
    if not matches:
        raise ValueError(f"Unexpected reply {reply!r} for {enum_cls.__name__}")
    return max(matches, key=lambda m: len(str(m.raw_value)))


def parse_error(reply: str) -> dict:
    """Splits an error queue entry into its code and message."""
    code, _, message = reply.partition(",")
    return {"code": int(code), "message": unquote(message)}


class State(BaseEnum):
    OFF = (0, "Off")
    ON = (1, "On")


class StatusRegister(BaseEnum):
    MEASUREMENT = ("MEAS", "Measurement")
    OPERATION = ("OPER", "Operation")
    QUESTIONABLE = ("QUES", "Questionable")


class FilterControl(BaseEnum):
    MOVING = ("MOV", "Moving")
    REPEAT = ("REP", "Repeat")


class TraceFeed(BaseEnum):
    SENSE = ("SENS1", "Pre-math readings")
    CALCULATE = ("CALC1", "Post-math readings")
    NONE = ("NONE", "None")


class TraceControl(BaseEnum):
    NEXT = ("NEXT", "Next")
    NEVER = ("NEV", "Never")
