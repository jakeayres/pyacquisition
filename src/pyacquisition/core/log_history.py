"""The recent log messages, kept in memory, so that an interface can show what
was logged before it connected, and then follow the log live.

`LogHistory` takes every message the logger broadcasts (those at or above its
GUI level), keeps the last `max_entries`, and gives each the next sequence
number. A client merges the snapshot with the stream as it does for the data
(see core/history.py):

1. Connect to `/stream/logs`, and hold the entries that arrive.
2. Fetch `/logs/history`. Its `seq` is the number of the last entry it includes.
3. Drop the held entries numbered `seq` or lower, and add the rest in order,
   and then every entry after them.
"""

import asyncio
from collections import deque

from .broadcaster import Broadcaster
from .consumer import Consumer
from .logging import logger

LEVELS = ("trace", "debug", "info", "warning", "error", "exception")


class LogHistory(Broadcaster, Consumer):
    """The recent log messages, and a stream of each as it is logged."""

    def __init__(self, source=logger, max_entries: int = 5000):
        """
        Args:
            source: Where the messages come from: the logger, which keeps its
                recent messages (see `Logger.recent_since`).
            max_entries (int): The most messages kept. Past that, the oldest are
                dropped.

        Messages are kept from when the history is made, but it only listens
        once it is set up, catching up on those logged in between from the
        logger's recent ones. The logger is shared by everything in the process,
        so a history listening from the start would fill up for ever if its
        experiment were made and never run (as tests do by the hundred).
        """
        Broadcaster.__init__(self)
        self.queue = asyncio.Queue()
        self._callbacks = []
        self._async_callbacks = []
        self._shutdown_event = asyncio.Event()

        self.max_entries = max_entries
        self.seq = 0  # the number of the last entry
        self.entries = deque(maxlen=max_entries)
        self._source = source
        self._start = source.sent  # the last message before this history
        self._listening = False

    def listen(self) -> None:
        """Adds the messages logged since the history was made, then every one
        after them, as it is logged. Nothing can be logged in between, since
        nothing here waits."""
        if self._listening:
            return
        for message in self._source.recent_since(self._start):
            self.add(message)
        self._source.subscribe(self)
        self._listening = True

    def stop_listening(self) -> None:
        if self._listening:
            self._source.unsubscribe(self)
            self._listening = False

    def add(self, message: dict) -> dict:
        """Stores a message from the logger, and broadcasts it. Returns the
        entry."""
        self.seq += 1
        level = str(message.get("level", "info")).lower()
        entry = {
            "type": "log",
            "seq": self.seq,
            "time": message.get("time"),
            "level": level if level in LEVELS else "info",
            "message": str(message.get("message", "")),
        }
        self.entries.append(entry)
        self.broadcast_sync(entry)
        return entry

    def snapshot(self) -> dict:
        """Every message kept, oldest first."""
        return {
            "seq": self.seq,
            "max_entries": self.max_entries,
            "entries": list(self.entries),
        }

    # ------------------------------------------------------------ the component
    async def setup(self):
        logger.debug("[LogHistory] Setup started")
        self.listen()
        logger.debug("[LogHistory] Setup completed")

    async def run(self, experiment) -> None:
        while True:
            try:
                message = await self.consume(timeout=0.1)
                if message is not None:
                    self.add(message)
                if self._shutdown_event.is_set():
                    break
            except Exception as e:  # noqa: BLE001 - one bad message must not stop it
                # Not logged, since that would come straight back here.
                print(f"[LogHistory] Error storing a log message: {e}")

    async def teardown(self):
        logger.debug("[LogHistory] Teardown started")
        self.stop_listening()
        logger.debug("[LogHistory] Teardown completed")

    async def shutdown(self):
        logger.debug("[LogHistory] Shutdown started")
        self._shutdown_event.set()

    def _register_endpoints(self, api_server):
        @api_server.app.get("/logs/history", tags=["logs"])
        async def logs_history():
            """
            The recent log messages, oldest first, as `entries`, each with its
            `seq`, `time` (seconds since the epoch), `level` and `message`.
            `max_entries` is the most kept. `seq` is the number of the last entry
            included: follow `/stream/logs` from there.
            """
            return {"status": 200, "data": self.snapshot()}
