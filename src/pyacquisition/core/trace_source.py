"""Taking traces: what a user declares (`Trace`), and what runs it
(`TraceSource`).

A trace is taken on demand (`acquire()`, a task, the API), and, if it is given
`every`, on a clock of its own as well. Each one taken is numbered in its data
file (from 0), handed to its listeners (the trace scribe, which writes it), and
waits in a queue until the rack's next row takes its number as the row's
`<name>_index`: so the index sits on the first row after the trace, and each
row takes at most one.
"""

import asyncio
import inspect
import math
import time
from collections import deque

from .instrument import resolve_enum_kwargs
from .logging import logger
from .measurement import check_unit
from .trace import TraceData
from .trace_file import TraceRecord

DEFAULT_TIMEOUT = 600.0  # seconds, when neither the driver nor the Trace says
READY_EVERY = 0.1  # seconds between asking whether an acquisition is done


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
        name: The trace's name. Its rows' column is `<name>_index`, and its
            traces are the `<name>` group of the data file's `.h5`.
        method: The instrument's trace method (marked `@mark_trace`), such as
            `generator.get_spectrum`.
        every: Seconds between traces taken on a clock of its own. Without it,
            a trace is only taken when asked for (`acquire()`, the
            `AcquireTrace` task, or `/traces/<name>/acquire`).
        unit: The channels' unit, if the driver's isn't the one to show.
        x_unit: The axis's unit, likewise.
        timeout: Seconds a trace may take before it is stopped. Defaults to the
            driver's, or 10 minutes.
        **kwargs: Given to each phase of the method (start, ready, the fetch
            and stop) that takes a parameter of that name.

    Raises:
        TypeError: If `method` isn't an instrument's trace method.
        ValueError: If a keyword argument is taken by no phase, or `every` or
            `timeout` isn't above 0.

    Example:
        Trace("spectrum", generator.get_spectrum, every=5)
    """

    def __init__(self, name: str, method, every: float | None = None, unit: str | None = None,
                 x_unit: str | None = None, timeout: float | None = None, **kwargs):
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
        self.name = name
        self.method = method
        self.instrument = method.__self__
        self.every = every
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

    @property
    def source(self) -> str:
        """Where it comes from, as `instrument.method`."""
        return f"{getattr(self.instrument, '_uid', '')}.{self.method.__name__}"

    @property
    def index_column(self) -> str:
        """The rows' column that holds each trace's number."""
        return f"{self.name}_index"

    def call(self, phase: str):
        """A phase's call, with the inputs it takes."""
        return _call(self.phases[phase], **self._kwargs[phase])


class TraceSource:
    """Runs one trace: takes it when asked, or on its clock, and links each one
    taken to a row.

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
        self._stopping = asyncio.Event()

    @property
    def name(self) -> str:
        return self.trace.name

    def _snapshot(self) -> dict:
        return {
            k: float(v)
            for k, v in self.latest_row().items()
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
        }

    def _number(self, data_file: str) -> int:
        """The next number in the data file's traces, from 0 in a new one."""
        current, number = self._numbered
        if data_file != current:
            number = 0
        self._numbered = (data_file, number + 1)
        return number

    async def acquire(self) -> TraceRecord | None:
        """Takes a trace now, and gives it (or None if it failed). One asked for
        while another is being taken waits for it, then takes its own.

        Raises:
            asyncio.CancelledError: If it is cancelled, after `stop` is called.
        """
        async with self._lock:
            trace = self.trace
            time_start, rows_start, row_start = time.time(), self.rows_written(), self._snapshot()
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
                row=self._snapshot(),
            )
            self.latest = record
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

    def row_columns(self, row: dict) -> dict:
        """The columns this trace adds to a row: the number of the oldest trace
        waiting (a trace of this data file), or NaN if none is."""
        data_file = self.data_file()
        while self._waiting:
            record = self._waiting.popleft()
            if record.data_file == data_file:
                return {self.trace.index_column: record.index}
            # Taken before the data file changed: its row is in the file before.
        return {self.trace.index_column: math.nan}

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
