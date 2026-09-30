"""Taking traces: what a user declares (`Trace`), and what runs it
(`TraceSource`).

A trace is taken in one of three ways:
- **with the rows** (`every_rows`): within the rack's cycle, every Nth row, and
  the row waits for it, so its columns are that row's;
- **on its own clock** (`every`), between rows;
- **on demand only** (neither): `acquire()`, a task, the API.

Any trace can also be taken on demand. Each one taken is numbered in its data
file (from 0), handed to its listeners (the trace scribe, which writes it), and
its columns go on a row: `<name>_index`, and its reductions (a mean, a peak's
position, …). In row mode that is its own row; otherwise it waits in a queue
for the rack's next row, and each row takes at most one.
"""

import asyncio
import inspect
import math
import time
from collections import deque
from collections.abc import Callable
from typing import Any

import numpy as np

from .instrument import resolve_enum_kwargs
from .logging import logger
from .measurement import check_unit
from .trace import TraceData
from .trace_file import TraceRecord

DEFAULT_TIMEOUT = 600.0  # seconds, when neither the driver nor the Trace says
READY_EVERY = 0.1  # seconds between asking whether an acquisition is done


def _peak_x(values, x):
    return x[int(np.nanargmax(values))]


def _integral(values, x):
    return np.trapezoid(values, x)


# The reductions that can be named (in TOML too), and the unit each column has:
# "unit" is the trace's, "x_unit" its axis's, None none.
REDUCTIONS = {
    "mean": (lambda values, x: np.nanmean(values), "unit"),
    "min": (lambda values, x: np.nanmin(values), "unit"),
    "max": (lambda values, x: np.nanmax(values), "unit"),
    "sum": (lambda values, x: np.nansum(values), "unit"),
    "std": (lambda values, x: np.nanstd(values), "unit"),
    "peak_x": (_peak_x, "x_unit"),
    "integral": (_integral, None),
}


async def _call(function, **kwargs):
    """Calls a phase, awaiting it if it is a coroutine."""
    answer = function(**kwargs)
    if inspect.isawaitable(answer):
        answer = await answer
    return answer


class Trace:
    """A trace to take: a measurement that is a whole array, such as a network
    analyser's sweep or a spectrometer's counts.

    Args:
        name: The trace's name. Its rows' columns start with it
            (`<name>_index`), and its traces are the `<name>` group of the data
            file's `.h5`.
        method: The instrument's trace method (marked `@mark_trace`), such as
            `generator.get_spectrum`.
        every: Seconds between traces taken on a clock of their own, between
            the rows.
        every_rows: Take a trace with every Nth row (1 for every row), within
            the rack's cycle: the row waits for it, and its columns are that
            row's. Not with `every`. With neither, a trace is only taken when
            asked for (`acquire()`, the `AcquireTrace` task, or
            `/traces/<name>/acquire`).
        unit: The channels' unit, if the driver's isn't the one to show.
        x_unit: The axis's unit, likewise.
        reduce: Columns made from each trace, on the row it belongs to (and
            empty on the others): the names of built-in reductions (`"mean"`,
            `"min"`, `"max"`, `"sum"`, `"std"`, `"peak_x"`, the axis value at
            the maximum, and `"integral"`, over the axis), or a dict of
            `{name: function}`, where a function takes a channel's values (and
            the axis as `x`, if it has a parameter called `x`) and gives a
            number. Each is made for every channel: the column is
            `<name>_<reduction>` for one channel, and
            `<name>_<channel>_<reduction>` for several.
        reduce_units: A reduction's unit, by its name, where it isn't the
            channels' (a built-in's is the channels', `peak_x`'s the axis's,
            and `integral`'s none).
        channels: The trace's channels, if the driver doesn't say, or says
            otherwise: they name the reductions' columns. Without either, a
            trace is taken to have one.
        timeout: Seconds a trace may take before it is stopped. Defaults to the
            driver's, or 10 minutes.
        **kwargs: Given to each phase of the method (start, ready, the fetch
            and stop) that takes a parameter of that name.

    Raises:
        TypeError: If `method` isn't an instrument's trace method.
        ValueError: If a keyword argument is taken by no phase; if `every` and
            `every_rows` are both given; if `every`, `every_rows` or `timeout`
            isn't above 0; or if a reduction isn't one there is.

    Example:
        ```python
        Trace("spectrum", generator.get_spectrum, every_rows=1, reduce=["mean", "peak_x"])
        ```
    """

    def __init__(self, name: str, method: Callable[..., TraceData], every: float | None = None,
                 every_rows: int | None = None, unit: str | None = None, x_unit: str | None = None,
                 reduce: list[str] | dict[str, Callable] | None = None,
                 reduce_units: dict | None = None, channels: list | None = None,
                 timeout: float | None = None, **kwargs: Any):
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"A trace needs a name, not {name!r}.")
        if not getattr(method, "_is_trace", False) or getattr(method, "__self__", None) is None:
            raise TypeError(
                f"Trace {name!r} needs an instrument's trace method (marked @mark_trace), "
                f"such as generator.get_spectrum, not {method!r}."
            )
        for label, value in (("every", every), ("timeout", timeout)):
            if value is not None and not value > 0:
                raise ValueError(f"Trace {name!r}: `{label}` must be above 0, not {value!r}.")
        if every_rows is not None and (isinstance(every_rows, bool) or not isinstance(every_rows, int)
                                       or every_rows < 1):
            raise ValueError(f"Trace {name!r}: `every_rows` must be a whole number from 1, not {every_rows!r}.")
        if every is not None and every_rows is not None:
            raise ValueError(f"Trace {name!r}: give `every` or `every_rows`, not both.")
        self.name = name
        self.method = method
        self.instrument = method.__self__
        self.every = every
        self.every_rows = every_rows
        self.unit = check_unit(unit, f"the unit of trace '{name}'")
        self.x_unit = check_unit(x_unit, f"the x unit of trace '{name}'")
        self.timeout = timeout or method._trace_timeout or DEFAULT_TIMEOUT
        self.phases = {
            phase: getattr(self.instrument, attr)
            for phase, attr in method._trace_phases.items()
            if attr is not None
        }
        self.phases["fetch"] = method
        # Each keyword argument goes to each phase that takes it.
        self._kwargs = {}
        for phase, function in self.phases.items():
            taken = inspect.signature(function).parameters
            self._kwargs[phase] = resolve_enum_kwargs(
                function, {k: v for k, v in kwargs.items() if k in taken}
            )
        unused = [k for k in kwargs if not any(k in self._kwargs[p] for p in self.phases)]
        if unused:
            raise ValueError(
                f"Trace {name!r}: {', '.join(map(repr, unused))} isn't an input of "
                f"{method.__name__} or its phases."
            )
        self.channels = self._channels(channels)
        self.reductions = self._reductions(reduce, reduce_units or {})

    def _channels(self, given) -> list | None:
        """The channels, as given, as the driver says, or None if unknown."""
        channels = given if given is not None else self.method._trace_channels
        if isinstance(channels, str):  # a method of the instrument's that says
            channels = getattr(self.instrument, channels)()
        if channels is None:
            return None
        channels = [str(c) for c in channels]
        if not channels:
            raise ValueError(f"Trace {self.name!r}: `channels` can't be empty.")
        return channels

    def _reductions(self, reduce, units: dict) -> list:
        """Each reduction's column, as (column, channel, reduction name, function,
        unit given, unit from). `channel` is None where the trace's channels
        aren't known: the first is used. `unit from` is where a unit not given
        comes from: "unit" (the channels'), "x_unit" (the axis's) or None."""
        if reduce is None:
            return []
        named = {r: r for r in reduce} if isinstance(reduce, (list, tuple)) else dict(reduce)
        found = []
        channels = self.channels or [None]
        for label, how in named.items():
            if isinstance(how, str):
                if how not in REDUCTIONS:
                    raise ValueError(
                        f"Trace {self.name!r}: there is no reduction called {how!r}; there are "
                        f"{', '.join(REDUCTIONS)}."
                    )
                function, unit_from = REDUCTIONS[how]
            elif callable(how):
                function, unit_from = how, "unit"
                if "x" not in inspect.signature(how).parameters:
                    function = (lambda f: lambda values, x: f(values))(how)
            else:
                raise ValueError(f"Trace {self.name!r}: reduction {label!r} must be a name or a function.")
            given = check_unit(units.get(label), f"the unit of reduction '{label}'")
            for channel in channels:
                column = f"{self.name}_{label}" if len(channels) == 1 else f"{self.name}_{channel}_{label}"
                found.append((column, channel, label, function, given, unit_from))
        return found

    @property
    def source(self) -> str:
        """Where it comes from, as `instrument.method`."""
        return f"{getattr(self.instrument, '_uid', '')}.{self.method.__name__}"

    @property
    def index_column(self) -> str:
        """The rows' column that holds each trace's number."""
        return f"{self.name}_index"

    @property
    def columns(self) -> list[str]:
        """The columns it adds to the rows: its index, then its reductions'."""
        return [self.index_column] + [column for column, *_ in self.reductions]

    def column_units(self, unit: str | None = None, x_unit: str | None = None) -> dict:
        """Each reduction column's unit, where it has one: the one given in
        `reduce_units`, or else the channels' (or, for `peak_x`, the axis's): the
        Trace's, or else `unit` and `x_unit` (a trace's, as its driver gives
        them)."""
        units = {"unit": self.unit or unit, "x_unit": self.x_unit or x_unit, None: None}
        found = {}
        for column, _, _, _, given, unit_from in self.reductions:
            if given or units[unit_from]:
                found[column] = given or units[unit_from]
        return found

    def call(self, phase: str):
        """A phase's call, with the inputs it takes."""
        return _call(self.phases[phase], **self._kwargs[phase])


class TraceSource:
    """Runs one trace: takes it when asked, with the rows or on its clock, and
    puts its columns on a row.

    It is told where it is by the experiment: `data_file()` (the current data
    file's name), `rows_written()` (the rows the scribe has written to it),
    `latest_row()` (the latest row's values) and `paused()` (whether the
    measurements are paused). Each trace taken goes to each of `listeners`.
    """

    def __init__(self, trace: Trace, *, data_file=lambda: "", rows_written=lambda: 0,
                 latest_row=dict, paused=lambda: False):
        self.trace = trace
        self.data_file = data_file
        self.rows_written = rows_written
        self.latest_row = latest_row
        self.paused = paused
        self.listeners = []
        self.latest: TraceRecord | None = None
        self._lock = asyncio.Lock()
        self._numbered: tuple[str, int] = ("", 0)  # the data file, and its next number
        self._waiting = deque()  # finished, for the next rows
        self._rows = 0  # rows seen, for `every_rows`
        self._due = False  # a row-mode trace failed, and the next row tries again
        self._failing = set()  # reductions failing, logged once until they work again
        self._channels_warned = False
        self._stopping = asyncio.Event()

    @property
    def name(self) -> str:
        return self.trace.name

    @staticmethod
    def _numbers(values: dict) -> dict:
        return {
            k: float(v)
            for k, v in values.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
        }

    def _number(self, data_file: str) -> int:
        """The next number in the data file's traces, from 0 in a new one."""
        current, number = self._numbered
        if data_file != current:
            number = 0
        self._numbered = (data_file, number + 1)
        return number

    def _reduce(self, data: TraceData) -> dict:
        """The reductions' values, by column: NaN for one that fails."""
        values = {}
        channels = list(data.channels)
        if self.trace.channels is None and len(channels) > 1 and not self._channels_warned and self.trace.reductions:
            self._channels_warned = True
            logger.warning(
                f"[Trace {self.name}] It has the channels {', '.join(channels)}, but none were declared, "
                f"so its reductions are of {channels[0]} only. Give Trace(channels=[...]) for each's."
            )
        x = data.axis()
        for column, channel, label, function, _, _ in self.trace.reductions:
            source = data.channels.get(channel if channel is not None else channels[0])
            try:
                if source is None:
                    raise KeyError(f"the trace has no channel {channel!r}")
                value = float(function(source, x))
                self._failing.discard(column)
            except Exception as error:  # noqa: BLE001 - a reduction failing leaves its cell empty
                value = math.nan
                if column not in self._failing:
                    self._failing.add(column)
                    logger.error(f"[Trace {self.name}] Reduction {label!r} failed: {error}")
            values[column] = value
        return values

    def _empty(self) -> dict:
        return dict.fromkeys(self.trace.columns, math.nan)

    def _columns(self, record: TraceRecord) -> dict:
        return {self.trace.index_column: record.index, **record.columns}

    async def acquire(self, row: dict | None = None) -> TraceRecord | None:
        """Takes a trace now, and gives it (or None if it failed). One asked for
        while another is being taken waits for it, then takes its own.

        Args:
            row: For a trace taken with the rows: its row's measurements, which
                are both of its snapshots, and it isn't queued for another row.

        Raises:
            asyncio.CancelledError: If it is cancelled, after `stop` is called.
        """
        async with self._lock:
            trace = self.trace
            snapshot = (lambda: self._numbers(row)) if row is not None else (lambda: self._numbers(self.latest_row()))
            time_start, rows_start, row_start = time.time(), self.rows_written(), snapshot()
            try:
                async with asyncio.timeout(trace.timeout):
                    if "start" in trace.phases:
                        await trace.call("start")
                    if "ready" in trace.phases:
                        while not await trace.call("ready"):
                            await asyncio.sleep(READY_EVERY)
                    data = await trace.call("fetch")
            except asyncio.CancelledError:
                await self._stop("it was cancelled")
                raise
            except TimeoutError:
                await self._stop(f"it took longer than {trace.timeout:g} s")
                logger.error(f"[Trace {self.name}] Not taken: it took longer than {trace.timeout:g} s.")
                return None
            except Exception as error:  # noqa: BLE001 - a failed trace is logged, not raised
                logger.error(f"[Trace {self.name}] Not taken: {type(error).__name__}: {error}")
                return None
            if not isinstance(data, TraceData):
                logger.error(
                    f"[Trace {self.name}] Not taken: {trace.source} gave a "
                    f"{type(data).__name__}, not a TraceData."
                )
                return None
            if trace.unit or trace.x_unit:
                data = TraceData(data.channels, x=data.x, x_name=data.x_name,
                                 x_unit=trace.x_unit or data.x_unit, unit=trace.unit or data.unit)
            data_file = self.data_file()
            record = TraceRecord(
                name=self.name,
                index=self._number(data_file),
                data=data,
                data_file=data_file,
                time_start=time_start,
                time=time.time(),
                rows_start=rows_start,
                rows=self.rows_written(),
                row_start=row_start,
                row=snapshot(),
                columns=self._reduce(data),
            )
            self.latest = record
            if row is None:
                self._waiting.append(record)
            for listener in self.listeners:
                try:
                    listener(record)
                except Exception as error:  # noqa: BLE001 - one listener mustn't stop the rest
                    logger.error(f"[Trace {self.name}] A listener failed: {error}")
            return record

    async def _stop(self, why: str) -> None:
        if "stop" not in self.trace.phases:
            return
        try:
            await asyncio.shield(self.trace.call("stop"))
        except Exception as error:  # noqa: BLE001
            logger.error(f"[Trace {self.name}] Couldn't stop it after {why}: {error}")

    async def row_columns(self, row: dict) -> dict:
        """The columns this trace adds to a row, which the rack calls with the
        row's measurements. In row mode, on a row that is due (every
        `every_rows`th, or the next after one that failed), a trace is taken
        now, and they are its. Otherwise they are the oldest waiting trace's (of
        this data file), or empty."""
        every_rows = self.trace.every_rows
        if every_rows is not None:
            due = self._due or self._rows % every_rows == 0
            self._rows += 1
            if due:
                record = await self.acquire(row=row)
                self._due = record is None
                return self._columns(record) if record is not None else self._empty()
        data_file = self.data_file()
        while self._waiting:
            record = self._waiting.popleft()
            if record.data_file == data_file:
                return self._columns(record)
            # Taken before the data file changed: its row is in the file before.
        return self._empty()

    async def run(self) -> None:
        """Takes a trace every `every` seconds (from start to start, or at once
        if the last ran long), except while the measurements are paused, until
        `shutdown`. Does nothing without `every`."""
        every = self.trace.every
        if every is None:
            return
        while not self._stopping.is_set():
            if self.paused():
                await self._wait(0.1)
                continue
            started = time.monotonic()
            await self.acquire()
            await self._wait(max(0.0, every - (time.monotonic() - started)))

    async def _wait(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stopping.wait(), seconds)
        except TimeoutError:
            pass

    def shutdown(self) -> None:
        self._stopping.set()
