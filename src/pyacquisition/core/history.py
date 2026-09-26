"""The recent data, kept in memory, so that an interface can show a whole file's
data as soon as it connects, and then follow it live.

`History` takes every row after the calculations, and keeps two segments: the
data since the current data file started, and the data of the file before it.

Every event, a row or the start of a new data file, gets the next sequence
number, and is broadcast (to the `/stream/data` websocket) once it is stored. A
client merges the snapshot with the stream without gaps or duplicates:

1. Connect to `/stream/data`, and hold the events that arrive.
2. Fetch `/history`. Its `seq` is the number of the last event it includes.
3. Drop the held events numbered `seq` or lower, and apply the rest in order,
   and then every event after them.

Applying an event: a `row` is appended to the current segment. A `new_file`
names the current segment if it has no rows yet; otherwise the current segment
becomes the previous one (the older previous one is dropped), and a new, empty
current segment starts with that name. A client that keeps rows as they arrive
keeps within `max_rows` (given in the snapshot) the same way: past it, it drops
the oldest rows, from the previous segment first, down to 99% of it.
"""

import array
import asyncio
import json
import math
import numbers
import struct
import sys
from enum import Enum

from fastapi import Query, Response
from fastapi.responses import StreamingResponse

from .broadcaster import Broadcaster
from .consumer import Consumer
from .logging import logger

NAN = float("nan")

# The binary form of `/history`: a little-endian uint32 giving the length of a
# JSON header, the header (padded with spaces to a multiple of 8 bytes, counting
# the 4 before it), then each segment's columns, in the order the header lists
# them, as little-endian float64s (NaN where there is no value).
BINARY_TYPE = "application/octet-stream"

JSON_PIECE = 20_000  # values encoded at a time in the JSON form (see _json_pieces)


def _number(value) -> float | None:
    """The value as a float, if it is a number (a bool counts, as 0 or 1)."""
    if isinstance(value, numbers.Real):
        return float(value)
    return None


def json_value(value):
    """The value as it is sent as JSON: a number (NaN and infinities become
    null), text, true or false, or null. An enum is sent as its label."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, numbers.Real):
        value = float(value)
        return value if math.isfinite(value) else None
    if isinstance(value, Enum):
        return str(getattr(value, "label", value.name))
    return str(value)


class Segment:
    """The rows of one data file, column by column."""

    def __init__(self, file: str | None = None):
        self.file = file
        self.rows = 0
        # Each numeric column, as float64s. A column that first appears part way
        # through is filled with NaN for the rows before it.
        self.columns: dict[str, array.array] = {}

    def append(self, values: dict[str, float]) -> None:
        for name in values:  # in the row's order, which the columns keep
            if name not in self.columns:
                self.columns[name] = array.array("d", [NAN]) * self.rows
        for name, column in self.columns.items():
            column.append(values.get(name, NAN))
        self.rows += 1

    def drop_oldest(self, count: int) -> None:
        for column in self.columns.values():
            del column[:count]
        self.rows -= count

    def describe(self) -> dict:
        return {"file": self.file, "rows": self.rows, "columns": list(self.columns)}


class History(Broadcaster, Consumer):
    """The recent rows, and a stream of each event as it happens."""

    def __init__(self, max_rows: int = 500_000):
        """
        Args:
            max_rows (int): The most rows kept, across both segments. Past that,
                the oldest are dropped, from the previous file first, down to 99%
                of it, so that rows are dropped in batches rather than one by one.
        """
        Broadcaster.__init__(self)
        self.queue = asyncio.Queue()
        self._callbacks = []
        self._async_callbacks = []
        self._shutdown_event = asyncio.Event()

        self.max_rows = max_rows
        # Dropping rows moves every row after them, so they are dropped in
        # batches of 1%, rather than one at a time as each new row arrives.
        self._batch = max(1, max_rows // 100)
        self.seq = 0  # the number of the last event
        self.previous: Segment | None = None
        self.current = Segment()
        self.latest = {}  # the last value of every column, numeric or not

    # ------------------------------------------------------------ events
    def add_row(self, row: dict) -> dict:
        """Stores a row, and broadcasts it. Returns the event."""
        self.seq += 1
        values = {name: json_value(value) for name, value in row.items()}
        self.current.append(
            {
                name: number
                for name, value in row.items()
                if (number := _number(value)) is not None
            }
        )
        self.latest.update(values)
        self._limit()
        event = {"type": "row", "seq": self.seq, "values": values}
        self.broadcast_sync(event)
        return event

    def new_file(self, file: str) -> dict:
        """Starts the segment for a new data file, and broadcasts it. Returns the
        event. The scribe calls it as each file starts."""
        self.seq += 1
        if self.current.rows:
            self.previous = self.current
            self.current = Segment(file)
        else:
            self.current.file = file
        event = {"type": "new_file", "seq": self.seq, "file": file}
        self.broadcast_sync(event)
        return event

    def _limit(self) -> None:
        segments = [s for s in (self.previous, self.current) if s is not None]
        excess = sum(s.rows for s in segments) - self.max_rows
        if excess <= 0:
            return
        # A batch more, so the next rows fit without dropping any more for a while.
        excess += self._batch
        for segment in segments:
            dropped = min(excess, segment.rows)
            segment.drop_oldest(dropped)
            excess -= dropped
        if self.previous is not None and self.previous.rows == 0:
            self.previous = None

    # ------------------------------------------------------------ snapshots
    def _segments(self) -> list[Segment]:
        return [s for s in (self.previous, self.current) if s is not None]

    def info(self) -> dict:
        """The shape of the history, without its data."""
        return {
            "seq": self.seq,
            "max_rows": self.max_rows,
            "segments": [s.describe() for s in self._segments()],
        }

    def _frozen(self) -> dict:
        """A copy of everything, taken at once, so it can be turned into JSON
        elsewhere while rows keep arriving. Copying the columns is quick."""
        segments = []
        for segment in self._segments():
            description = segment.describe()
            description["columns"] = {
                name: array.array("d", column)
                for name, column in segment.columns.items()
            }
            segments.append(description)
        return {
            "seq": self.seq,
            "max_rows": self.max_rows,
            "latest": dict(self.latest),
            "segments": segments,
        }

    @staticmethod
    def _as_json(frozen: dict) -> dict:
        for segment in frozen["segments"]:
            segment["columns"] = {
                name: [value if math.isfinite(value) else None for value in column]
                for name, column in segment["columns"].items()
            }
        return frozen

    def snapshot_json(self) -> dict:
        """Everything in the history, with each column as a list (null for NaN)."""
        return self._as_json(self._frozen())

    @classmethod
    async def _json_pieces(cls, frozen: dict):
        """The JSON response for a snapshot, a piece at a time.

        A large history takes seconds to turn into JSON, and the encoder holds the
        GIL for as long as each call takes (so a thread would not help). Encoding
        a few thousand values at a time, and letting the loop run in between,
        keeps the experiment running meanwhile.
        """
        head = json.dumps(
            {
                "seq": frozen["seq"],
                "max_rows": frozen["max_rows"],
                "latest": frozen["latest"],
            }
        )
        yield '{"status": 200, "data": ' + head[:-1] + ', "segments": ['
        for i, segment in enumerate(frozen["segments"]):
            meta = json.dumps({"file": segment["file"], "rows": segment["rows"]})
            yield ("," if i else "") + meta[:-1] + ', "columns": {'
            for j, (name, column) in enumerate(segment["columns"].items()):
                yield ("," if j else "") + json.dumps(name) + ": ["
                for start in range(0, len(column), JSON_PIECE):
                    part = column[start : start + JSON_PIECE]
                    values = [v if math.isfinite(v) else None for v in part]
                    yield ("," if start else "") + json.dumps(values)[1:-1]
                    await asyncio.sleep(0)
                yield "]"
            yield "}}"
        yield "]}}"

    def snapshot_binary(self) -> bytes:
        """Everything in the history, in the binary form (see BINARY_TYPE)."""
        segments = self._segments()
        header = json.dumps(
            {
                "seq": self.seq,
                "max_rows": self.max_rows,
                "latest": self.latest,
                "segments": [s.describe() for s in segments],
            }
        ).encode()
        header += b" " * (-(4 + len(header)) % 8)
        parts = [struct.pack("<I", len(header)), header]
        for segment in segments:
            for column in segment.columns.values():
                if sys.byteorder == "big":
                    column = array.array("d", column)
                    column.byteswap()
                parts.append(column.tobytes())
        return b"".join(parts)

    # ------------------------------------------------------------ the component
    async def setup(self):
        logger.debug("[History] Setup started")
        logger.debug("[History] Setup completed")

    async def run(self, experiment) -> None:
        while True:
            try:
                row = await self.consume(timeout=0.1)
                if row is not None:
                    self.add_row(row)
                if self._shutdown_event.is_set():
                    break
            except Exception as e:  # noqa: BLE001 - one bad row must not stop it
                logger.error(f"[History] Error storing a row: {e}")

    async def teardown(self):
        logger.debug("[History] Teardown started")
        logger.debug("[History] Teardown completed")

    async def shutdown(self):
        logger.debug("[History] Shutdown started")
        self._shutdown_event.set()

    def _register_endpoints(self, api_server):
        @api_server.app.get("/history", tags=["history"])
        async def history(format: str = Query("json", pattern="^(json|binary)$")):
            """
            The data since the current file started, and the data of the file before
            it, as `segments` (oldest first), each with its `file`, its number of
            `rows` and its numeric `columns`. `latest` is the last value of every
            column, numeric or not. `seq` is the number of the last event included:
            follow `/stream/data` from there.

            `format=binary` gives the same, compactly: a little-endian uint32 giving
            the length of a JSON header (the above, with only column names), then
            the header, padded to a multiple of 8 bytes, then every column in
            order, as little-endian float64s.
            """
            if format == "binary":
                return Response(self.snapshot_binary(), media_type=BINARY_TYPE)
            return StreamingResponse(
                self._json_pieces(self._frozen()), media_type="application/json"
            )

        @api_server.app.get("/history/info", tags=["history"])
        async def history_info():
            """
            The shape of the history, without its data: the number of the last
            event, the most rows kept, and each segment's file, rows and columns.
            """
            return {"status": 200, "data": self.info()}
