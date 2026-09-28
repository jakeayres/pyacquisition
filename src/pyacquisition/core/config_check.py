"""Checking an experiment's config without running it, or opening an instrument.

`problems(config)` finds every problem with a config (a dict, as `tomllib` reads
a file), not only the first, and says where each one is, so that the setup page
(`pyacquisition new`) can show it by the field it belongs to. A config with no
problems loads with `Experiment.from_config`.
"""

import inspect
import typing
from dataclasses import dataclass
from enum import Enum

from ..instruments import instrument_map
from . import calculations, settings
from .adapters import ADAPTERS
from .config_parser import ConfigParser, trace_problem
from .instrument import SoftwareInstrument, enum_classes, resolve_enum_kwargs

# The keys an entry of each section can have.
INSTRUMENT_KEYS = ("instrument", "adapter", "resource", "args")
MEASUREMENT_KEYS = ("instrument", "method", "args", "unit")


@dataclass(frozen=True)
class Problem:
    """One problem with a config.

    Attributes:
        where: The keys that lead to it, such as
            `("measurements", "T", "args", "input_channel")`.
        message: What is wrong, in a sentence.
    """

    where: tuple
    message: str

    def to_json(self) -> dict:
        return {"where": list(self.where), "message": self.message}


def problems(config) -> list[Problem]:
    """Every problem with a config, in the order of its sections."""
    if not isinstance(config, dict):
        return [Problem((), "A config must be a table of sections.")]
    found = []
    for section in config:
        if section not in ConfigParser.ALLOWED_SECTIONS:
            found.append(
                Problem(
                    (section,),
                    f"There is no section [{section}]. The sections are "
                    f"{', '.join(ConfigParser.ALLOWED_SECTIONS)}.",
                )
            )
    found += _option_problems(config)
    found += _instrument_problems(config.get("instruments", {}))
    found += _measurement_problems(
        config.get("measurements", {}), config.get("instruments", {})
    )
    measured = config.get("measurements", {})
    found += [
        Problem(("calculations", *where), message)
        for where, message in calculations.config_problems(
            config.get("calculations", {}),
            list(measured) if isinstance(measured, dict) else [],
        )
    ]
    found += _trace_problems(config.get("traces", {}), config.get("instruments", {}))
    return found


# ---------------------------------------------------------------- options
def _option_problems(config: dict) -> list[Problem]:
    found = []
    for section in dict.fromkeys(s.section for s in settings.SETTINGS.values()):
        table = config.get(section, {})
        if not isinstance(table, dict):
            found.append(Problem((section,), f"[{section}] must be a table."))
            continue
        keys = {s.key: s for s in settings.SETTINGS.values() if s.section == section}
        for key, value in table.items():
            if (section, key) in settings.REMOVED_KEYS:
                continue  # does nothing now, and is let be
            if key not in keys:
                found.append(
                    Problem(
                        (section, key),
                        f"Unknown key '{key}' in [{section}]"
                        f"{settings._suggestion(key, keys)}. Valid keys: "
                        f"{', '.join(keys)}.",
                    )
                )
                continue
            try:
                keys[key].check(key, value)
            except ValueError as e:
                found.append(Problem((section, key), str(e)))
    return found


# ---------------------------------------------------------------- instruments
def _instrument_problems(instruments) -> list[Problem]:
    if not isinstance(instruments, dict):
        return [Problem(("instruments",), "[instruments] must be a table.")]
    found = []
    for name, entry in instruments.items():
        where = ("instruments", name)
        if not isinstance(entry, dict):
            found.append(Problem(where, f"Instrument '{name}' must be a table."))
            continue
        for key in entry:
            if key not in INSTRUMENT_KEYS:
                found.append(
                    Problem(
                        (*where, key),
                        f"Instrument '{name}': unknown key '{key}'. An instrument "
                        f"takes {', '.join(INSTRUMENT_KEYS)}.",
                    )
                )
        driver = entry.get("instrument")
        if driver is None:
            found.append(
                Problem(where, f"Instrument '{name}' needs `instrument`, naming its driver.")
            )
            continue
        if driver not in instrument_map:
            found.append(
                Problem(
                    (*where, "instrument"),
                    f"Instrument '{name}': there is no driver called {driver!r}.",
                )
            )
            continue
        found += _connection_problems(name, entry, instrument_map[driver])
    return found


def _connection_problems(name: str, entry: dict, cls) -> list[Problem]:
    where = ("instruments", name)
    found = []
    if issubclass(cls, SoftwareInstrument):
        for key in ("adapter", "resource", "args"):
            if key in entry:
                found.append(
                    Problem(
                        (*where, key),
                        f"Instrument '{name}': {cls.__name__} is a software "
                        f"instrument, which takes no `{key}`.",
                    )
                )
        return found
    adapter = entry.get("adapter")
    if adapter is None:
        found.append(
            Problem(
                (*where, "adapter"),
                f"Instrument '{name}' needs `adapter`: one of {', '.join(ADAPTERS)}.",
            )
        )
    elif adapter not in ADAPTERS:
        found.append(
            Problem(
                (*where, "adapter"),
                f"Instrument '{name}': there is no adapter called {adapter!r}. "
                f"The adapters are {', '.join(ADAPTERS)}.",
            )
        )
    resource = entry.get("resource")
    if not isinstance(resource, str) or not resource:
        found.append(
            Problem(
                (*where, "resource"),
                f"Instrument '{name}' needs `resource`: its address, such as "
                '"GPIB0::7::INSTR".',
            )
        )
    args = entry.get("args", {})
    if not isinstance(args, dict):
        found.append(
            Problem((*where, "args"), f"Instrument '{name}': `args` must be a table.")
        )
        return found
    timeout = args.get("timeout")
    if timeout is not None and (
        isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0
    ):
        found.append(
            Problem(
                (*where, "args", "timeout"),
                f"Instrument '{name}': `timeout` must be a whole number of "
                f"milliseconds, above 0, got {timeout!r}.",
            )
        )
    for key in ("read_termination", "write_termination"):
        if key in args and not isinstance(args[key], str):
            found.append(
                Problem(
                    (*where, "args", key),
                    f'Instrument \'{name}\': `{key}` must be text, such as "\\n", '
                    f"got {args[key]!r}.",
                )
            )
    return found


# ---------------------------------------------------------------- measurements
def _measurement_problems(measurements, instruments) -> list[Problem]:
    if not isinstance(measurements, dict):
        return [Problem(("measurements",), "[measurements] must be a table.")]
    if not isinstance(instruments, dict):
        instruments = {}
    found = []
    for name, entry in measurements.items():
        where = ("measurements", name)
        if not isinstance(entry, dict):
            found.append(Problem(where, f"Measurement '{name}' must be a table."))
            continue
        for key in entry:
            if key not in MEASUREMENT_KEYS:
                found.append(
                    Problem(
                        (*where, key),
                        f"Measurement '{name}': unknown key '{key}'. A measurement "
                        f"takes {', '.join(MEASUREMENT_KEYS)}.",
                    )
                )
        if "unit" in entry and not isinstance(entry["unit"], str):
            found.append(
                Problem(
                    (*where, "unit"),
                    f'Measurement \'{name}\': `unit` must be text, such as "K", '
                    f"got {entry['unit']!r}.",
                )
            )
        instrument = entry.get("instrument")
        if instrument is None:
            found.append(
                Problem(where, f"Measurement '{name}' needs `instrument`, naming one.")
            )
            continue
        if instrument not in instruments:
            found.append(
                Problem(
                    (*where, "instrument"),
                    f"Measurement '{name}': there is no instrument '{instrument}' "
                    "in [instruments].",
                )
            )
            continue
        driver = instruments[instrument]
        cls = instrument_map.get(driver.get("instrument")) if isinstance(driver, dict) else None
        if cls is None:
            continue  # the instrument's own problem says why
        found += _method_problems(name, entry, cls)
    return found


def queries(cls) -> dict:
    """A driver's queries, which are what can be measured, by name."""
    return {query.__name__: query for query in cls._queries}


def _method_problems(name: str, entry: dict, cls) -> list[Problem]:
    where = ("measurements", name)
    method = entry.get("method")
    if method is None:
        return [Problem(where, f"Measurement '{name}' needs `method`, naming a query.")]
    found = queries(cls)
    if method not in found:
        if method in {command.__name__ for command in cls._commands}:
            message = (
                f"Measurement '{name}': {method!r} is a command of {cls.__name__}, "
                "which acts rather than reads, so it can't be measured."
            )
        else:
            message = (
                f"Measurement '{name}': {cls.__name__} has no query {method!r}. "
                f"Its queries are {', '.join(sorted(found))}."
            )
        return [Problem((*where, "method"), message)]
    args = entry.get("args", {})
    if not isinstance(args, dict):
        return [Problem((*where, "args"), f"Measurement '{name}': `args` must be a table.")]
    return _argument_problems(name, found[method], args)


def _argument_problems(
    name: str, function, args: dict, section: str = "measurements"
) -> list[Problem]:
    """Whether `args` bind to a method's signature (without `self`), with enum
    text resolved and the simple types checked, from the class alone."""
    where = (section, name, "args")
    what = {"measurements": "Measurement", "traces": "Trace"}[section]
    parameters = list(inspect.signature(function).parameters.values())[1:]
    try:
        hints = typing.get_type_hints(function)
    except Exception:  # noqa: BLE001 - a hint that can't be resolved: not checked
        hints = {}
    found = []
    known = {p.name for p in parameters}
    for key in args:
        if key not in known:
            found.append(
                Problem(
                    (*where, key),
                    f"{what} '{name}': {function.__name__} takes no `{key}`"
                    + (f". It takes {', '.join(sorted(known))}." if known else "."),
                )
            )
    for parameter in parameters:
        if parameter.name not in args:
            if parameter.default is inspect.Parameter.empty and parameter.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                found.append(
                    Problem(
                        (*where, parameter.name),
                        f"{what} '{name}': {function.__name__} needs "
                        f"`{parameter.name}`.",
                    )
                )
            continue
        value = args[parameter.name]
        annotation = hints.get(parameter.name, parameter.annotation)
        problem = _value_problem(function, parameter.name, annotation, value)
        if problem:
            found.append(Problem((*where, parameter.name), f"{what} '{name}': {problem}"))
    return found


# ---------------------------------------------------------------- traces
def _trace_problems(traces, instruments) -> list[Problem]:
    if not isinstance(traces, dict):
        return [Problem(("traces",), "[traces] must be a table.")]
    if not isinstance(instruments, dict):
        instruments = {}
    found = []
    for name, entry in traces.items():
        where = ("traces", name)
        problem = trace_problem(name, entry, instruments)
        if problem:
            found.append(Problem(where, problem))
            continue
        driver = instruments[entry["instrument"]]
        cls = instrument_map.get(driver.get("instrument")) if isinstance(driver, dict) else None
        if cls is None:
            continue  # the instrument's own problem says why
        methods = {trace.__name__: trace for trace in cls._traces}
        if entry["method"] not in methods:
            found.append(
                Problem(
                    (*where, "method"),
                    f"Trace '{name}': {cls.__name__} has no trace {entry['method']!r}. "
                    f"Its traces are {', '.join(sorted(methods)) or 'none'}.",
                )
            )
            continue
        found += _argument_problems(name, methods[entry["method"]], entry.get("args", {}), "traces")
    return found


def _value_problem(function, key: str, annotation, value) -> str | None:
    try:
        value = resolve_enum_kwargs(function, {key: value})[key]
    except ValueError as e:
        return str(e)
    if isinstance(value, Enum):
        return None
    enums = enum_classes(annotation)
    if enums and not isinstance(value, str):
        names = ", ".join(member.name for enum in enums for member in enum)
        return f"`{key}` must name one of {names}, got {value!r}"
    wanted = {int: "a whole number", float: "a number", str: "text", bool: "true or false"}
    if annotation not in wanted:
        return None  # not a kind that is checked
    fits = {
        int: isinstance(value, int) and not isinstance(value, bool),
        float: isinstance(value, (int, float)) and not isinstance(value, bool),
        str: isinstance(value, str),
        bool: isinstance(value, bool),
    }[annotation]
    return None if fits else f"`{key}` must be {wanted[annotation]}, got {value!r}"
