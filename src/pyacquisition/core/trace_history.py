"""The recent traces, kept in memory and thinned for the page, so that it can
show the latest trace and a map of the ones before it as soon as it connects,
and then follow them live.

A trace longer than `bins` points is kept as that many bins, each with the min,
max and mean of its points, so a narrow spike survives in its bin's max. A
shorter one is kept whole. Either way its values are kept as float32, which is
plenty to draw. The latest trace of each is also kept at full resolution, for
`full=true` (the trace panel's CSV export).

Every event, a trace stored or the start of a new data file, gets the next
sequence number, and is broadcast (to the `/stream/traces` websocket) once it is
stored. A page follows a trace without gaps or duplicates as it follows the rows
(see `history.py`):

1. Connect to `/stream/traces`, and hold the events that arrive.
2. Fetch `/traces/<name>/history`. Its `seq` is the number of the last event it
   includes.
3. Drop the held events numbered `seq` or lower, and apply the rest in order,
   and then every event after them. Each event's `seq` is one more than the one
   before (whichever trace it is of), so a gap means one was missed.

Applying a `trace` event of the trace followed: fetch
`/traces/<name>/history?after=<the seq of the last one held>`, which gives each
stored since. A `new_file` event: the traces of files before the one before it
are dropped, as they are here.

The traces kept are those of the current data file and the one before it, and
the latest of each trace whatever its file, within `budget_mb`: past it, the
oldest are dropped first (but never a trace's latest).
"""

import json
import math
import struct
from collections import deque
from dataclasses import dataclass, field

import numpy as np
from fastapi import HTTPException, Query, Response

from .broadcaster import Broadcaster
from .trace_file import TraceRecord

BINS = 1024  # a trace longer than this is binned to this many bins
BUDGET_MB = 64

# The binary form of `/traces/<name>/latest` and `/history`: a little-endian
# uint32 giving the length of a JSON header, the header (padded with spaces to a
# multiple of 8 bytes, counting the 4 before it), then the arrays. The header
# lists each trace's arrays as `blocks`: `{"part", "channel", "dtype", "offset",
# "length"}`, where `part` is "x" (the axis, "f8"), or a channel's "min", "max"
# and "mean" (binned) or "values" (not), `dtype` is "f4" or "f8" (little-endian
# floats), `offset` is in bytes from the end of the header, and `length` is in
# values. Each array is padded to a multiple of 8 bytes, so each can be read in
# place.
BINARY_TYPE = "application/octet-stream"


def bin_starts(points: int, bins: int) -> np.ndarray:
    """Where each bin starts, for `points` points in `bins` bins: as even as can
    be, each of `points // bins` or one more."""
    return (np.arange(bins) * points) // bins


def _binned(values: np.ndarray, starts: np.ndarray) -> dict:
    """A channel's min, max and mean in each bin, NaN ignored (NaN for a bin of
    nothing else)."""
    values = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(values)
    sums = np.add.reduceat(np.where(finite, values, 0.0), starts)
    counts = np.add.reduceat(finite.astype(np.int64), starts)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(counts > 0, sums / counts, np.nan)
    return {
        "min": np.fmin.reduceat(values, starts).astype(np.float32),
        "max": np.fmax.reduceat(values, starts).astype(np.float32),
        "mean": mean.astype(np.float32),
    }


@dataclass
class Thinned:
    """One trace, as the page is sent it."""

    seq: int
    record: TraceRecord
    binned: bool
    x: np.ndarray  # float64: each point's axis value, or each bin's mean
    values: dict  # channel: {"min", "max", "mean"} or {"values"}, of arrays
    nbytes: int = field(init=False)

    def __post_init__(self):
        self.nbytes = self.x.nbytes + sum(
            array.nbytes for parts in self.values.values() for array in parts.values()
        )

    @classmethod
    def of(cls, seq: int, record: TraceRecord, bins: int = BINS, full: bool = False) -> "Thinned":
        """The trace thinned to `bins` bins if it is longer, or whole (in its
        own precision, with `full`)."""
        data = record.data
        axis = data.axis()
        if full or data.points <= bins:
            cast = (lambda a: a) if full else (lambda a: a.astype(np.float32))
            values = {name: {"values": cast(v)} for name, v in data.channels.items()}
            return cls(seq, record, False, np.asarray(axis, dtype=np.float64), values)
        starts = bin_starts(data.points, bins)
        sizes = np.diff(np.append(starts, data.points))
        x = np.add.reduceat(np.asarray(axis, dtype=np.float64), starts) / sizes
        values = {name: _binned(v, starts) for name, v in data.channels.items()}
        return cls(seq, record, True, x, values)

    def header(self) -> dict:
        """Everything but the arrays."""
        record, data = self.record, self.record.data
        axis = (
            {"kind": "linear", "start": data.x[0], "stop": data.x[1]}
            if data.linear
            else {"kind": "explicit"}
        )
        return {
            "seq": self.seq,
            "name": record.name,
            "index": record.index,
            "data_file": record.data_file,
            "time_start": record.time_start,
            "time": record.time,
            "points": data.points,
            "binned": self.binned,
            "length": len(self.x),
            "axis": axis,
            "x_name": data.x_name,
            "x_unit": data.x_unit,
            "unit": data.unit,
            "channels": list(data.channels),
            "row_start": record.row_start,
            "row": record.row,
            "columns": {k: _json_number(v) for k, v in record.columns.items()},
        }

    def arrays(self):
        """(part, channel, array) for each array, in the order they are sent."""
        yield "x", None, self.x
        for channel, parts in self.values.items():
            for part, array in parts.items():
                yield part, channel, array


def _json_number(value):
    value = float(value)
    return value if math.isfinite(value) else None


def _json_list(array: np.ndarray) -> list:
    values = array.tolist()
    if np.isfinite(array).all():
        return values
    return [v if math.isfinite(v) else None for v in values]


def as_json(top: dict, traces: list[Thinned]) -> dict:
    """Traces as `format=json` sends them, after `top` (the history's `seq`
    and the like): each header, with `x` and `values` (channel: {part: list},
    null for NaN)."""
    return {
        **top,
        "traces": [
            {
                **trace.header(),
                "x": _json_list(trace.x),
                "values": {
                    channel: {part: _json_list(array) for part, array in parts.items()}
                    for channel, parts in trace.values.items()
                },
            }
            for trace in traces
        ],
    }


def as_binary(top: dict, traces: list[Thinned]) -> bytes:
    """Traces in the binary form (see BINARY_TYPE), after `top`."""
    headers, parts, offset = [], [], 0
    for trace in traces:
        blocks = []
        for part, channel, array in trace.arrays():
            dtype = "f4" if array.dtype == np.float32 else "f8"
            raw = np.ascontiguousarray(array, dtype="<" + dtype).tobytes()
            raw += b"\0" * (-len(raw) % 8)
            blocks.append(
                {"part": part, "channel": channel, "dtype": dtype, "offset": offset,
                 "length": len(array)}
            )
            parts.append(raw)
            offset += len(raw)
        headers.append({**trace.header(), "blocks": blocks})
    header = json.dumps({**top, "traces": headers}).encode()
    header += b" " * (-(4 + len(header)) % 8)
    return b"".join([struct.pack("<I", len(header)), header, *parts])


class TraceHistory(Broadcaster):
    """The recent traces, thinned, and a stream of each event as it happens."""

    def __init__(self, budget_mb: float = BUDGET_MB, bins: int = BINS):
        """
        Args:
            budget_mb: The most memory the traces kept may take, in MB (the
                latest of each at full resolution counts too). Past it, the
                oldest are dropped first, but never a trace's latest.
            bins: The most points a trace is kept with: a longer one is binned.
        """
        super().__init__()
        self.budget = budget_mb * 1e6
        self.bins = bins
        self.seq = 0  # the number of the last event
        self.file: str | None = None  # the current data file, and the one before
        self.previous_file: str | None = None
        self._traces: dict[str, deque[Thinned]] = {}
        self._latest: dict[str, Thinned] = {}  # each trace's latest, thinned

    # ------------------------------------------------------------ events
    def add(self, record: TraceRecord) -> dict:
        """Stores a trace just taken, and broadcasts it. Returns the event."""
        self.seq += 1
        thinned = Thinned.of(self.seq, record, self.bins)
        self._traces.setdefault(record.name, deque()).append(thinned)
        self._latest[record.name] = thinned
        self._limit()
        event = {"type": "trace", "seq": self.seq, "name": record.name,
                 "index": record.index, "time": record.time}
        self.broadcast_sync(event)
        return event

    def new_file(self, file: str) -> dict:
        """Notes a new data file, dropping the traces of the files before the
        one before it, and broadcasts it. Returns the event. The scribe calls it
        as each file starts."""
        self.seq += 1
        if file != self.file:
            self.previous_file, self.file = self.file, file
        kept = {self.file, self.previous_file}
        for name, traces in self._traces.items():
            latest = self._latest.get(name)
            self._traces[name] = deque(
                t for t in traces if t.record.data_file in kept or t is latest
            )
        event = {"type": "new_file", "seq": self.seq, "file": file}
        self.broadcast_sync(event)
        return event

    @property
    def nbytes(self) -> int:
        """The memory the traces take: thinned, and the latest at full size."""
        thinned = sum(t.nbytes for traces in self._traces.values() for t in traces)
        return thinned + sum(t.record.data.nbytes for t in self._latest.values())

    def _limit(self) -> None:
        excess = self.nbytes - self.budget
        while excess > 0:
            oldest = min(
                (traces for name, traces in self._traces.items()
                 if traces and traces[0] is not self._latest[name]),
                key=lambda traces: traces[0].seq,
                default=None,
            )
            if oldest is None:
                return  # only the latest are left
            excess -= oldest.popleft().nbytes

    # ------------------------------------------------------------ snapshots
    def latest(self, name: str) -> Thinned | None:
        return self._latest.get(name)

    def history(self, name: str, after: int | None = None) -> list[Thinned]:
        """A trace's traces kept, oldest first; with `after`, those stored
        after that event only."""
        traces = self._traces.get(name, ())
        return [t for t in traces if after is None or t.seq > after]

    def _register_endpoints(self, api_server, names):
        """The endpoints, for the traces `names()` gives."""

        def known(name: str) -> None:
            if name not in names():
                raise HTTPException(status_code=404, detail=f"There is no trace called {name!r}.")

        def respond(traces: list[Thinned], name: str, format: str):
            top = {
                "seq": self.seq,
                "name": name,
                "file": self.file,
                "previous_file": self.previous_file,
                "budget_mb": self.budget / 1e6,
            }
            if format == "binary":
                return Response(as_binary(top, traces), media_type=BINARY_TYPE)
            return {"status": 200, "data": as_json(top, traces)}

        @api_server.app.get("/traces/{name}/latest", tags=["traces"])
        async def latest(
            name: str,
            format: str = Query("binary", pattern="^(json|binary)$"),
            full: bool = False,
        ):
            """
            The trace's latest, thinned for the page: `traces` holds it (one),
            with its `seq`, `index`, `data_file`, times, `points`, whether it is
            `binned` (to 1024 bins, each with its `min`, `max` and `mean`) and
            its `length` then, its `axis`, `x_name`, `x_unit`, `unit`,
            `channels`, both row snapshots (`row_start`, `row`) and its
            reductions (`columns`). `seq` is the number of the last event: follow
            `/stream/traces` from there. `file` and `previous_file` are the data
            files whose traces are kept, and `budget_mb` the memory they may
            take.

            `full=true` gives the trace at full resolution, in its own
            precision. `format=json` gives the values as lists (`x`, and
            `values`: channel: part: list, null for NaN); the binary form (the
            default) gives a little-endian uint32 giving the length of a JSON
            header, the header (padded to a multiple of 8 bytes), then the
            arrays, each listed in its trace's `blocks` with its `part`,
            `channel`, `dtype` (`f4` or `f8`), `offset` (bytes from the header's
            end) and `length`. 404 for a trace there isn't, or none taken yet.
            """
            known(name)
            thinned = self.latest(name)
            if thinned is None:
                raise HTTPException(status_code=404, detail=f"No {name} trace has been taken yet.")
            if full:
                thinned = Thinned.of(thinned.seq, thinned.record, full=True)
            return respond([thinned], name, format)

        @api_server.app.get("/traces/{name}/history", tags=["traces"])
        async def history(
            name: str,
            format: str = Query("binary", pattern="^(json|binary)$"),
            after: int | None = None,
        ):
            """
            The trace's recent traces, thinned for the page, oldest first, in
            the form of `/traces/<name>/latest`: those of the current data file
            and the one before it (within the memory they may take), and the
            latest. `after` gives only those stored after that event's `seq`.
            `seq` is the number of the last event included: follow
            `/stream/traces` from there.
            """
            known(name)
            return respond(self.history(name, after), name, format)
