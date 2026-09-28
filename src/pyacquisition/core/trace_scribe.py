"""Writing traces to their trace files (trace_file.py), off the event loop.

`TraceScribe` takes each trace as it is made (`add`) and writes those waiting,
all at once, on a worker thread: one open, append, flush and close of the file
per batch, as the scribe appends to its CSV. Nothing holds the file open
between writes, so a notebook can read it meanwhile.

A write that can't open the file, because another program has it open (Windows'
HDF5 refuses a writer while a reader holds the file), leaves the traces waiting
in memory, and they are tried again every few seconds. One warning says so, and
one message when writing starts again. Past `pending_mb` of waiting traces, the
oldest are dropped, with an error saying how many.

A data file's traces roll over to a new part (`00.01 sweep.001.h5`) once its
latest part is past `file_mb`, so a file damaged in a crash costs only its part.
"""

import asyncio
import re
from collections import deque
from pathlib import Path

from .logging import logger
from .trace_file import SUFFIX, TraceFileBusy, TraceRecord, append, trace_path

TAG = "[TraceScribe]"


class TraceScribe:
    """Writes traces to their data files' trace files, in the order they came.

    Args:
        folder: The data folder, where the data files and their trace files are.
        file_mb: The size past which a data file's traces go on in a new part.
        pending_mb: The most traces kept waiting while the file can't be
            written, in megabytes. Past it, the oldest are dropped.
        retry_every: Seconds between tries while the file can't be written.
    """

    def __init__(self, folder, *, file_mb: float = 500.0, pending_mb: float = 256.0, retry_every: float = 5.0):
        self.folder = Path(folder)
        self.file_mb = file_mb
        self.pending_mb = pending_mb
        self.retry_every = retry_every
        self._pending: deque[TraceRecord] = deque()
        self._in_flight = 0  # the oldest pending, being written now
        self._parts: dict[str, int] = {}  # by data file: the part being written
        self._waiting = False  # whether writes are failing and being retried
        self._wake = asyncio.Event()
        self._done = asyncio.Event()
        self._done.set()
        self._stopping = False
        self.written = 0  # traces written, all told

    # ------------------------------------------------------------ taking traces
    def add(self, record: TraceRecord) -> None:
        """Takes a trace to write. It returns at once."""
        self._pending.append(record)
        self._done.clear()
        self._drop_oldest()
        self._wake.set()

    @property
    def pending(self) -> int:
        """Traces waiting to be written."""
        return len(self._pending)

    def _drop_oldest(self) -> None:
        limit = self.pending_mb * 1e6
        dropped = 0
        while sum(r.nbytes for r in self._pending) > limit and len(self._pending) > self._in_flight + 1:
            del self._pending[self._in_flight]
            dropped += 1
        if dropped:
            logger.error(
                f"{TAG} {dropped} trace{'s' if dropped != 1 else ''} dropped: more than "
                f"{self.pending_mb:g} MB were waiting to be written, as the trace file can't be."
            )

    # ------------------------------------------------------------ the files
    def _part(self, data_file: str) -> int:
        """The part a data file's traces go to now: its latest, or the next once
        that is past `file_mb`."""
        if data_file not in self._parts:
            stem = re.escape(Path(data_file).stem)
            numbered = [
                int(m.group(1))
                for p in (self.folder.iterdir() if self.folder.is_dir() else [])
                if (m := re.fullmatch(rf"{stem}\.(\d{{3}}){re.escape(SUFFIX)}", p.name))
            ]
            self._parts[data_file] = max(numbered, default=0)
        part = self._parts[data_file]
        path = trace_path(self.folder, data_file, part)
        if path.exists() and path.stat().st_size > self.file_mb * 1e6:
            part += 1
            self._parts[data_file] = part
        return part

    def _write(self, batch: list[TraceRecord]) -> None:
        """Writes a batch, one file at a time, in order. Runs on the worker thread."""
        self.folder.mkdir(parents=True, exist_ok=True)
        start = 0
        while start < len(batch):
            data_file = batch[start].data_file
            end = start
            while end < len(batch) and batch[end].data_file == data_file:
                end += 1
            part = self._part(data_file)
            append(trace_path(self.folder, data_file, part), batch[start:end], part=part)
            start = end

    # ------------------------------------------------------------ the worker
    async def run(self) -> None:
        """Writes the traces as they come, until `shutdown`. A write happens on a
        worker thread, one at a time, so the event loop carries on meanwhile."""
        while True:
            if not self._pending:
                self._done.set()
                if self._stopping:
                    return
                self._wake.clear()
                await self._wake.wait()
                continue
            batch = list(self._pending)
            self._in_flight = len(batch)
            try:
                await asyncio.to_thread(self._write, batch)
            except TraceFileBusy as error:
                self._in_flight = 0
                if not self._waiting:
                    self._waiting = True
                    logger.warning(
                        f"{TAG} The trace file can't be written: another program has it "
                        f"open. The traces wait, and are written once it is closed. ({error})"
                    )
                if self._stopping:
                    logger.error(f"{TAG} {len(self._pending)} traces weren't written, as the file stayed open.")
                    self._pending.clear()
                    continue
                self._wake.clear()
                try:
                    await asyncio.wait_for(self._wake.wait(), self.retry_every)
                except TimeoutError:
                    pass
                continue
            except Exception as error:  # noqa: BLE001 - a bad trace mustn't stop the rest
                logger.error(f"{TAG} {len(batch)} traces couldn't be written: {error}")
            else:
                self.written += len(batch)
                if self._waiting:
                    self._waiting = False
                    logger.info(f"{TAG} The trace file is written again: {len(batch)} waiting traces written.")
            for _ in batch:
                self._pending.popleft()
            self._in_flight = 0

    async def flush(self, timeout: float | None = None) -> None:
        """Waits until every trace taken so far is written (or dropped)."""
        await asyncio.wait_for(self._done.wait(), timeout)

    def shutdown(self) -> None:
        """Asks `run` to write what is waiting, trying once, and then stop."""
        self._stopping = True
        self._wake.set()
