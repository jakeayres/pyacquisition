"""Verification specs: a TOML file beside each instrument class.

`keithley_6221.py` is described by `keithley_6221.toml` in the same folder. The
spec says what the engine may do to that instrument, and nothing it does not
list is ever written. The whole spec is checked against the class when it is
loaded, and a typo is an error, never a silent default.

    [identity]                  # *IDN? must contain all of these
    contains = ["KEITHLEY", "6221"]

    [guard]                     # messages that are reads, besides those with '?'
    read = ['^R\\d+$']

    [safe_state]                # required for any check that writes
    steps = [{ call = "set_output_state", args = { state = "OFF" } }]
    verify = [{ call = "get_output_state", equals = "OFF" }]

    [read.get_buffer_selected]  # how to run a getter that needs help
    skip = "why it is not run"          # or:
    args = [{ start = 1, count = 1 }]   # arguments to call it with
    requires = ["nanovoltmeter"]        # capabilities the inventory must list
    range = [0, 500]                    # the reading must lie in this range

    [roundtrip.current]         # set_current / get_current, unless named
    hazard = "reversible"       # required: "reversible" or "hazardous"
    values = [1e-9, -1e-9]      # written in turn, or "*" for every enum member
    select = { line = ["TOP", "BOTTOM"] }   # other arguments, tried in every combination
    rel = 1e-6                  # how closely the readback must match
    abs = 0.0
    preconditions = [{ call = "get_output_state", equals = "OFF" }]
"""

import inspect
import re
import tomllib
import typing
from dataclasses import dataclass, field, replace
from enum import Enum
from itertools import product
from pathlib import Path

from .model import Hazard, SpecError

_MISSING = object()


@dataclass(frozen=True)
class Call:
    """A method to call, with its arguments and, for a condition, the value expected."""

    call: str
    args: dict = field(default_factory=dict)
    equals: object = _MISSING


@dataclass(frozen=True)
class ReadRule:
    skip: str | None = None
    args: tuple | None = None
    requires: tuple = ()
    range: tuple | None = None
    hazard: Hazard = Hazard.READ_ONLY
    note: str = ""


@dataclass(frozen=True)
class RoundTrip:
    id: str
    setter: str
    getter: str
    hazard: Hazard
    values: object
    param: str | None = None
    select: dict = field(default_factory=dict)
    rel: float = 1e-6
    abs: float = 0.0
    requires: tuple = ()
    preconditions: tuple = ()
    note: str = ""


@dataclass(frozen=True)
class Spec:
    identity: tuple | None = None
    read_patterns: tuple = ()
    steps: tuple | None = None  # None: no [safe_state], so nothing may be written
    verify: tuple = ()
    read: dict = field(default_factory=dict)
    roundtrips: dict = field(default_factory=dict)
    path: Path | None = None


# ---------------------------------------------------------------- parsing
def _only(table, allowed, where):
    unknown = set(table) - set(allowed)
    if unknown:
        raise SpecError(
            f"{where}: unknown key(s) {sorted(unknown)}, expected some of {sorted(allowed)}"
        )


def _table(value, where):
    if not isinstance(value, dict):
        raise SpecError(f"{where}: expected a table")
    return value


def _strings(value, where):
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return tuple(value)
    raise SpecError(f"{where}: expected a string or a list of strings")


def _hazard(text, where):
    try:
        return Hazard.parse(text)
    except ValueError as error:
        raise SpecError(f"{where}: {error}") from None


def _calls(value, where, *, equals):
    if not isinstance(value, list):
        raise SpecError(f"{where}: expected a list of tables")
    calls = []
    for i, item in enumerate(value):
        here = f"{where}[{i}]"
        item = _table(item, here)
        _only(item, {"call", "args"} | ({"equals"} if equals else set()), here)
        if "call" not in item:
            raise SpecError(f"{here}: 'call' is required")
        if equals and "equals" not in item:
            raise SpecError(f"{here}: 'equals' is required")
        calls.append(
            Call(item["call"], dict(item.get("args", {})), item.get("equals", _MISSING))
        )
    return tuple(calls)


def parse_spec(data, source="<spec>"):
    """Builds a `Spec` from parsed TOML, raising `SpecError` for anything unexpected."""
    _only(data, {"identity", "guard", "safe_state", "read", "roundtrip"}, source)

    identity = None
    if "identity" in data:
        table = _table(data["identity"], f"{source} [identity]")
        _only(table, {"contains"}, f"{source} [identity]")
        identity = _strings(table.get("contains", []), f"{source} [identity] contains")
        if not identity:
            raise SpecError(f"{source} [identity]: 'contains' is empty")

    read_patterns = ()
    if "guard" in data:
        table = _table(data["guard"], f"{source} [guard]")
        _only(table, {"read"}, f"{source} [guard]")
        read_patterns = _strings(table.get("read", []), f"{source} [guard] read")
        for pattern in read_patterns:
            try:
                re.compile(pattern)
            except re.error as error:
                raise SpecError(f"{source} [guard]: bad pattern {pattern!r}: {error}")

    steps, verify = None, ()
    if "safe_state" in data:
        table = _table(data["safe_state"], f"{source} [safe_state]")
        _only(table, {"steps", "verify"}, f"{source} [safe_state]")
        steps = _calls(
            table.get("steps", []), f"{source} [safe_state] steps", equals=False
        )
        verify = _calls(
            table.get("verify", []), f"{source} [safe_state] verify", equals=True
        )

    read = {}
    for name, rule in _table(data.get("read", {}), f"{source} [read]").items():
        where = f"{source} [read.{name}]"
        rule = _table(rule, where)
        _only(rule, {"skip", "args", "requires", "range", "hazard", "note"}, where)
        args = rule.get("args")
        if args is not None:
            if isinstance(args, dict):
                args = (args,)
            elif isinstance(args, list):
                args = tuple(args)
            if not isinstance(args, tuple) or not all(
                isinstance(a, dict) for a in args
            ):
                raise SpecError(f"{where}: 'args' must be a table or a list of tables")
        bounds = rule.get("range")
        if bounds is not None and not (
            isinstance(bounds, list)
            and len(bounds) == 2
            and all(isinstance(b, int | float) for b in bounds)
        ):
            raise SpecError(f"{where}: 'range' must be [low, high]")
        read[name] = ReadRule(
            skip=rule.get("skip"),
            args=args,
            requires=_strings(rule.get("requires", []), f"{where} requires"),
            range=tuple(bounds) if bounds else None,
            hazard=_hazard(rule.get("hazard", "read-only"), where),
            note=rule.get("note", ""),
        )

    roundtrips = {}
    for id, table in _table(data.get("roundtrip", {}), f"{source} [roundtrip]").items():
        where = f"{source} [roundtrip.{id}]"
        table = _table(table, where)
        _only(
            table,
            {
                "setter",
                "getter",
                "param",
                "values",
                "select",
                "hazard",
                "rel",
                "abs",
                "requires",
                "preconditions",
                "note",
            },
            where,
        )
        if "hazard" not in table:
            raise SpecError(
                f"{where}: 'hazard' is required ('reversible' or 'hazardous'), "
                "so that every write is tagged deliberately"
            )
        hazard = _hazard(table["hazard"], where)
        if hazard is Hazard.READ_ONLY:
            raise SpecError(f"{where}: a round trip writes, so it cannot be read-only")
        values = table.get("values")
        if values != "*" and not (isinstance(values, list) and values):
            raise SpecError(f"{where}: 'values' must be a non-empty list, or \"*\"")
        select = _table(table.get("select", {}), f"{where} select")
        for name, choices in select.items():
            if choices != "*" and not (isinstance(choices, list) and choices):
                raise SpecError(
                    f'{where}: select.{name} must be a non-empty list, or "*"'
                )
        roundtrips[id] = RoundTrip(
            id=id,
            setter=table.get("setter", f"set_{id}"),
            getter=table.get("getter", f"get_{id}"),
            hazard=hazard,
            values=values,
            param=table.get("param"),
            select=dict(select),
            rel=float(table.get("rel", 1e-6)),
            abs=float(table.get("abs", 0.0)),
            requires=_strings(table.get("requires", []), f"{where} requires"),
            preconditions=_calls(
                table.get("preconditions", []), f"{where} preconditions", equals=True
            ),
            note=table.get("note", ""),
        )

    return Spec(
        identity=identity,
        read_patterns=read_patterns,
        steps=steps,
        verify=verify,
        read=read,
        roundtrips=roundtrips,
    )


def spec_path(cls):
    """Where the spec for an instrument class lives: beside its source file."""
    return Path(inspect.getsourcefile(cls)).with_suffix(".toml")


def load_spec(cls):
    """Loads and validates the spec beside an instrument class.

    Returns:
        Spec: The spec, or None if the class has none.

    Raises:
        SpecError: If the spec is malformed or does not fit the class.
    """
    path = spec_path(cls)
    if not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise SpecError(f"{path.name}: {error}") from None
    spec = parse_spec(data, path.name)
    spec = replace(spec, path=path)
    validate(spec, cls)
    return spec


# ---------------------------------------------------------------- the class
def marked_methods(cls):
    """The methods of a class that are registered as queries or commands."""
    found = {}
    for name in dir(cls):
        member = getattr(cls, name, None)
        if callable(member) and (
            hasattr(member, "_is_query") or hasattr(member, "_is_command")
        ):
            found[name] = member
    return found


def params_of(func):
    """The names of a method's parameters, without `self`."""
    return [name for name in inspect.signature(func).parameters if name != "self"]


def hints_of(func):
    return typing.get_type_hints(func)


def _is_enum(annotation):
    return isinstance(annotation, type) and issubclass(annotation, Enum)


def coerce(value, annotation, where="value"):
    """Converts a value from a spec to what a method's parameter takes.

    Enum members are given by name, so `"OFF"` becomes `State.OFF`.
    """
    if annotation is None or annotation is inspect.Parameter.empty:
        return value
    origin = typing.get_origin(annotation)
    try:
        if _is_enum(annotation):
            if isinstance(value, annotation):
                return value
            try:
                return annotation[value]
            except (KeyError, TypeError):
                names = [member.name for member in annotation]
                raise SpecError(f"{where}: {value!r} is not one of {names}") from None
        if annotation is bool:
            if not isinstance(value, bool):
                raise SpecError(f"{where}: {value!r} is not true or false")
            return value
        if annotation is int:
            if isinstance(value, bool) or int(value) != value:
                raise SpecError(f"{where}: {value!r} is not a whole number")
            return int(value)
        if annotation is float:
            if isinstance(value, bool):
                raise SpecError(f"{where}: {value!r} is not a number")
            return float(value)
        if annotation is str:
            return str(value)
        if origin is list or annotation is list:
            (item,) = typing.get_args(annotation) or (None,)
            return [coerce(v, item, where) for v in value]
    except (TypeError, ValueError) as error:
        raise SpecError(f"{where}: {error}") from None
    return value


def bind(func, raw, where):
    """Checks a call's arguments against a method and converts them."""
    params, hints = params_of(func), hints_of(func)
    unknown = set(raw) - set(params)
    if unknown:
        raise SpecError(
            f"{where}: {func.__name__} has no parameter(s) {sorted(unknown)}"
        )
    kwargs = {
        name: coerce(value, hints.get(name), f"{where} {name}")
        for name, value in raw.items()
    }
    try:
        inspect.signature(func).bind(object(), **kwargs)
    except TypeError as error:
        raise SpecError(f"{where}: {func.__name__}: {error}") from None
    return kwargs


def domain(annotation, raw, where):
    """The values to try for a parameter: `"*"` means every member of an enum."""
    if raw == "*":
        if _is_enum(annotation):
            return list(annotation)
        raise SpecError(f'{where}: "*" only works for enum parameters')
    return [coerce(value, annotation, where) for value in raw]


def compatible(value_annotation, getter_annotation):
    """Whether what a getter returns can be given back to the setter to restore it."""
    if _is_enum(value_annotation):
        return value_annotation is getter_annotation
    numbers = (int, float)
    if value_annotation in numbers and getter_annotation in numbers:
        return True
    # `==`, not `is`: two `list[int]` annotations are equal but not the same object
    return value_annotation == getter_annotation


def roundtrip_shape(rt, cls):
    """Works out how a round trip calls its setter and getter.

    Returns:
        tuple: The value parameter, the values to write, and the argument sets
            for the other parameters, one per combination.

    Raises:
        SpecError: If the round trip does not fit the class.
    """
    where = f"[roundtrip.{rt.id}]"
    methods = marked_methods(cls)
    setter, getter = methods.get(rt.setter), methods.get(rt.getter)
    if setter is None:
        raise SpecError(f"{where}: {cls.__name__} has no method {rt.setter!r}")
    if getter is None:
        raise SpecError(f"{where}: {cls.__name__} has no method {rt.getter!r}")
    if not rt.getter.startswith("get_"):
        raise SpecError(f"{where}: the getter {rt.getter!r} must be named get_...")

    params, hints = params_of(setter), hints_of(setter)
    if not params:
        raise SpecError(f"{where}: {rt.setter} takes no value to write")
    param = rt.param or params[-1]
    if param not in params:
        raise SpecError(f"{where}: {rt.setter} has no parameter {param!r}")

    other = [p for p in params if p != param]
    extra = set(rt.select) - set(other)
    if extra:
        raise SpecError(
            f"{where}: select names {sorted(extra)}, not parameters of {rt.setter}"
        )
    required = {
        n
        for n, p in inspect.signature(setter).parameters.items()
        if n != "self" and n != param and p.default is inspect.Parameter.empty
    }
    missing = required - set(rt.select)
    if missing:
        raise SpecError(
            f"{where}: {rt.setter} also needs {sorted(missing)}, give them in 'select'"
        )

    getter_params = params_of(getter)
    unsupplied = set(getter_params) - set(rt.select)
    if unsupplied:
        raise SpecError(
            f"{where}: {rt.getter} takes {sorted(unsupplied)}, give them in 'select'"
        )

    returns = hints_of(getter).get("return")
    if not compatible(hints.get(param), returns):
        raise SpecError(
            f"{where}: {rt.getter} returns {getattr(returns, '__name__', returns)} but "
            f"{rt.setter} takes {getattr(hints.get(param), '__name__', hints.get(param))}, "
            "so the original value could not be restored"
        )

    values = domain(hints.get(param), rt.values, f"{where} values")
    names = list(rt.select)
    choices = [domain(hints.get(n), rt.select[n], f"{where} select.{n}") for n in names]
    selects = (
        [dict(zip(names, combo)) for combo in product(*choices)] if names else [{}]
    )
    return param, values, selects


def validate(spec, cls):
    """Checks a spec against an instrument class, raising `SpecError` if it does not fit."""
    problems = []
    methods = marked_methods(cls)

    def check(action):
        try:
            action()
        except SpecError as error:
            problems.append(str(error))

    for name, rule in spec.read.items():
        where = f"[read.{name}]"
        if name not in methods:
            problems.append(f"{where}: {cls.__name__} has no method {name!r}")
            continue
        if not name.startswith("get_"):
            problems.append(f"{where}: only getters (get_...) can be read")
            continue
        for args in rule.args or ():
            check(
                lambda name=name, args=args, where=where: bind(
                    methods[name], args, where
                )
            )

    def check_call(call, where):
        func = methods.get(call.call)
        if func is None:
            problems.append(f"{where}: {cls.__name__} has no method {call.call!r}")
            return
        check(lambda: bind(func, call.args, where))
        if call.equals is not _MISSING:
            if not call.call.startswith("get_"):
                problems.append(
                    f"{where}: a condition must call a getter, not {call.call!r}"
                )
            else:
                check(
                    lambda: coerce(
                        call.equals, hints_of(func).get("return"), f"{where} equals"
                    )
                )

    for i, call in enumerate(spec.steps or ()):
        check_call(call, f"[safe_state] steps[{i}]")
    for i, call in enumerate(spec.verify):
        check_call(call, f"[safe_state] verify[{i}]")
    for rt in spec.roundtrips.values():
        check(lambda rt=rt: roundtrip_shape(rt, cls))
        for i, call in enumerate(rt.preconditions):
            check_call(call, f"[roundtrip.{rt.id}] preconditions[{i}]")

    if problems:
        raise SpecError(
            f"{cls.__name__} spec has {len(problems)} problem(s):\n  "
            + "\n  ".join(problems)
        )


# ---------------------------------------------------------------- comparing
def same(got, want, rel=0.0, abs_tol=0.0):
    """Whether a value read back matches what was written."""
    if got == want:
        return True
    numeric = (int, float)
    if (
        isinstance(got, numeric)
        and isinstance(want, numeric)
        and not isinstance(got, bool)
        and not isinstance(want, bool)
    ):
        return abs(got - want) <= max(abs_tol, rel * abs(want))
    return False


def check_type(value, annotation):
    """Describes how a value differs from the type a method promises, or None if it matches."""
    origin = typing.get_origin(annotation) or annotation
    if not isinstance(origin, type):
        return None
    if origin is float:
        ok = isinstance(value, int | float) and not isinstance(value, bool)
    elif origin is int:
        ok = isinstance(value, int) and not isinstance(value, bool)
    else:
        ok = isinstance(value, origin)
    if ok:
        return None
    return f"returned {value!r} ({type(value).__name__}), expected {origin.__name__}"


def canned(annotation):
    """A stand-in value of a type, for a dry run whose replies mean nothing."""
    origin = typing.get_origin(annotation) or annotation
    if _is_enum(origin):
        return next(iter(origin))
    return {
        bool: False,
        int: 0,
        float: 0.0,
        str: "",
        dict: {},
        list: [],
        tuple: (),
    }.get(origin)
