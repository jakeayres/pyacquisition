"""Records the traffic with an instrument, so that it can be replayed later.

Run once in the lab with a real instrument, and the transcript becomes a fixture
that the `mock` adapter can replay in CI, checking that the driver still parses
what the instrument really said. Use it as an adapter, wrapping another one:

    [instruments]
    k = {instrument = "Keithley_6221", adapter = "record", resource = "GPIB0::12::INSTR",
         args = {inner = "pyvisa", transcript = "recordings/k6221.jsonl"}}

`inner` is the adapter that talks to the instrument (`pyvisa` if left out) and
`transcript` is the file the traffic is appended to. Any other `args` go to the
inner adapter. Replay it with `adapter = "mock"` and `args = {transcript = "..."}`.

The transcript has one JSON object per line, for example:

    {"time": "2026-09-19T12:00:00+00:00", "resource": "GPIB0::12::INSTR",
     "op": "query", "message": "SOUR:CURR?", "reply": "+1.000000E-03"}
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from .mock import _AnyResource


def record_adapter():
    """Returns a resource manager whose resources record their traffic."""
    return RecordingResourceManager()


def load_transcript(path):
    """Reads the replies to the queries in a transcript.

    Returns:
        dict: For each query message, the replies in the order they were given.
    """
    replies = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("op") == "query" and "reply" in event:
            replies.setdefault(event["message"], []).append(event["reply"])
    return replies


class RecordingResource:
    """A resource that logs what passes through it and otherwise behaves like it.

    Args:
        inner: The resource to record.
        transcript (str): The file to append the traffic to.
        resource_name (str): The name to log, taken from `inner` if left out.
    """

    def __init__(self, inner, transcript, resource_name=None):
        path = Path(transcript)
        path.parent.mkdir(parents=True, exist_ok=True)
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_file", open(path, "a", encoding="utf-8"))  # noqa: SIM115
        object.__setattr__(
            self, "_name", resource_name or getattr(inner, "resource_name", "")
        )

    def _log(self, **event):
        if self._file.closed:
            return
        event = {
            "time": datetime.now(UTC).isoformat(),
            "resource": self._name,
            **event,
        }
        self._file.write(json.dumps(event) + "\n")
        self._file.flush()

    def _record(self, op, method, message, *args, **kwargs):
        try:
            reply = method(message, *args, **kwargs)
        except Exception as error:
            self._log(op=op, message=message, error=f"{type(error).__name__}: {error}")
            raise
        if op == "write":
            self._log(op=op, message=message)
        else:
            self._log(op=op, message=message, reply=reply)
        return reply

    def write(self, message, *args, **kwargs):
        return self._record("write", self._inner.write, message, *args, **kwargs)

    def query(self, message, *args, **kwargs):
        return self._record("query", self._inner.query, message, *args, **kwargs)

    def read(self, *args, **kwargs):
        try:
            reply = self._inner.read(*args, **kwargs)
        except Exception as error:
            self._log(op="read", error=f"{type(error).__name__}: {error}")
            raise
        self._log(op="read", reply=reply)
        return reply

    def close(self):
        try:
            self._inner.close()
        finally:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def __setattr__(self, name, value):
        setattr(self._inner, name, value)


class RecordingResourceManager:
    """Opens resources through another adapter and records them."""

    def __init__(self):
        self.resources = {}
        self._managers = []

    def list_resources(self, query="?*::INSTR"):
        # the inner adapter is only known once a resource is opened, and it
        # reports any failure to open then
        return _AnyResource()

    def open_resource(self, resource_name, inner="pyvisa", transcript=None, **kwargs):
        """Opens a resource with the `inner` adapter, recording it to `transcript`."""
        if transcript is None:
            raise ValueError("The 'record' adapter needs args = {transcript = 'file'}")
        if inner == "record":
            raise ValueError("The 'record' adapter cannot record itself")

        from . import get_adapter

        manager = get_adapter(inner)
        resource = RecordingResource(
            manager.open_resource(resource_name, **kwargs), transcript, resource_name
        )
        self._managers.append(manager)
        self.resources[resource_name] = resource
        return resource

    def close(self):
        for resource in self.resources.values():
            resource.close()
        self.resources.clear()
        for manager in self._managers:
            close = getattr(manager, "close", None)
            if close is not None:
                close()
        self._managers.clear()
