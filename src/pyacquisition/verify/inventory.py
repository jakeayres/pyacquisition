"""The hardware inventory: which instruments are connected, and how far to trust a run.

It reuses the format of the `[instruments]` section of an experiment config, so
that opening an instrument here goes through the same adapters as a real run,
with one addition per instrument, a `verify` table:

    [instruments.k6221]
    instrument = "Keithley_6221"
    adapter = "pyvisa"
    resource = "GPIB0::12::INSTR"
    args = { read_termination = "\\n" }

    [instruments.k6221.verify]
    capabilities = ["nanovoltmeter"]   # what is attached, for checks that need it
    max_hazard = "reversible"          # this instrument is never asked for more
    skip = ["set_wave_function"]       # methods to leave alone here
    record = "recordings/k6221.jsonl"  # log the traffic, for replay in CI

`max_hazard` limits an instrument whatever the run asks for, so a magnet supply
that is cold and live can be pinned to `"read-only"` for good.
"""

import tomllib
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

from ..core.adapters.mock import MockResource
from ..core.adapters.record import RecordingResource
from ..core.instrument import Instrument
from .guard import GuardedResource
from .model import Hazard, SpecError
from .session import Session
from .spec import load_spec

_ENTRY_KEYS = {"instrument", "adapter", "resource", "args", "verify"}
_VERIFY_KEYS = {"capabilities", "max_hazard", "skip", "record"}


class Unreachable(Exception):
    """An instrument that could not be opened, with the reason."""


@dataclass
class Entry:
    """One instrument in the inventory."""

    name: str
    cls: type
    adapter: str | None
    resource: str | None
    args: dict = field(default_factory=dict)
    capabilities: tuple = ()
    max_hazard: Hazard | None = None
    skip: tuple = ()
    record: str | None = None


def load_inventory(path):
    """Reads an inventory file.

    Raises:
        SpecError: If it is malformed or names an instrument that is not hardware.
    """
    from ..instruments import instrument_map

    path = Path(path)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = []
    for name, table in data.get("instruments", {}).items():
        where = f"{path.name} [instruments.{name}]"
        unknown = set(table) - _ENTRY_KEYS
        if unknown:
            raise SpecError(f"{where}: unknown key(s) {sorted(unknown)}")
        verify = table.get("verify", {})
        unknown = set(verify) - _VERIFY_KEYS
        if unknown:
            raise SpecError(f"{where} verify: unknown key(s) {sorted(unknown)}")

        cls = instrument_map.get(table.get("instrument"))
        if cls is None:
            raise SpecError(f"{where}: unknown instrument {table.get('instrument')!r}")
        if not (isinstance(cls, type) and issubclass(cls, Instrument)):
            raise SpecError(f"{where}: {cls.__name__} is not a hardware instrument")

        limit = verify.get("max_hazard")
        try:
            limit = Hazard.parse(limit) if limit is not None else None
        except ValueError as error:
            raise SpecError(f"{where} verify: {error}") from None
        entries.append(
            Entry(
                name=name,
                cls=cls,
                adapter=table.get("adapter"),
                resource=table.get("resource"),
                args=dict(table.get("args", {})),
                capabilities=tuple(verify.get("capabilities", ())),
                max_hazard=limit,
                skip=tuple(verify.get("skip", ())),
                record=verify.get("record"),
            )
        )
    return entries


def build_session(entry, resource, policy, *, dry_run=False, spec=None):
    """Builds an instrument over a resource, behind the guard, and wraps it in a session.

    Constructing an instrument runs its own `__init__`, which for most sends a
    few setup commands. That is the same as using it in an experiment, so the
    guard's write window is open for it, and only for it.

    Raises:
        Unreachable: If the instrument does not initialise.
    """
    guard = GuardedResource(resource, spec.read_patterns if spec else ())
    try:
        with guard.writes_allowed():
            instrument = entry.cls(entry.name, guard)
    except Exception as error:  # noqa: BLE001 - any failure to initialise means unreachable
        with suppress(Exception):
            resource.close()
        raise Unreachable(
            f"{entry.cls.__name__} did not initialise: {type(error).__name__}: {error}"
        ) from None
    return Session(
        entry.name,
        instrument,
        guard,
        spec,
        policy,
        max_hazard=entry.max_hazard,
        capabilities=entry.capabilities,
        skip=entry.skip,
        dry_run=dry_run,
    )


def open_session(entry, policy, *, dry_run=False):
    """Connects to an inventory instrument and returns a session for it.

    With `dry_run` no device is contacted: the instrument runs over a stand-in
    that only records what it is sent.

    Raises:
        Unreachable: If the resource cannot be opened or the instrument does not initialise.
        SpecError: If the instrument's spec is invalid.
    """
    spec = load_spec(entry.cls)
    if dry_run:
        return build_session(
            entry,
            MockResource(entry.resource or entry.name),
            policy,
            dry_run=True,
            spec=spec,
        )

    if not entry.adapter or not entry.resource:
        raise Unreachable("the inventory gives no adapter and resource")

    from ..core.experiment import Experiment

    args = dict(entry.args)
    timeout = args.pop("timeout", 5000)
    adapter = Experiment._get_adapter_class(entry.adapter)
    resource = Experiment._open_resource(
        adapter, entry.resource, timeout=timeout, **args
    )
    if resource is None:
        raise Unreachable(
            f"could not open {entry.resource!r} with adapter {entry.adapter!r}"
        )
    if entry.record:
        resource = RecordingResource(resource, entry.record, entry.resource)
    return build_session(entry, resource, policy, spec=spec)
