"""The log history: recent log messages kept in memory for the GUI, and
streamed with a number for each, so a client can merge a snapshot with the
stream (milestone 7)."""

import asyncio
import socket

import pytest
from fastapi.testclient import TestClient

from pyacquisition.core.api_server import APIServer
from pyacquisition.core.broadcaster import Broadcaster
from pyacquisition.core.consumer import Consumer
from pyacquisition.core.log_history import LogHistory
from pyacquisition.core.logging import logger


def message(text, level="info", time=1.0):
    return {"time": time, "message": text, "level": level}


class Log(Broadcaster):
    """A stand-in for the logger: it keeps what it sends, as the logger does."""

    def __init__(self):
        super().__init__()
        self.sent = 0
        self.recent = []

    def send(self, text, level="info"):
        self.sent += 1
        self.recent.append((self.sent, message(text, level)))
        self.broadcast_sync(message(text, level))

    def recent_since(self, number):
        return [m for n, m in self.recent if n > number]


# -------------------------------------------------------------- entries
def test_each_message_gets_the_next_number():
    logs = LogHistory()

    assert logs.add(message("one")) == {
        "type": "log",
        "seq": 1,
        "time": 1.0,
        "level": "info",
        "message": "one",
    }
    assert logs.add(message("two"))["seq"] == 2
    assert logs.seq == 2


def test_only_the_most_recent_are_kept():
    logs = LogHistory(max_entries=3)
    for n in range(5):
        logs.add(message(str(n)))

    assert [entry["message"] for entry in logs.entries] == ["2", "3", "4"]
    assert logs.seq == 5  # numbering carries on past the dropped ones


def test_levels_are_lower_case_and_an_unknown_one_is_info():
    logs = LogHistory()

    assert logs.add(message("a", level="WARNING"))["level"] == "warning"
    assert logs.add(message("b", level="shout"))["level"] == "info"


def test_a_message_that_is_not_text_is_turned_into_text():
    logs = LogHistory()

    assert logs.add(message(ValueError("bad")))["message"] == "bad"


def test_each_message_is_broadcast_as_it_is_stored():
    logs = LogHistory()
    listener = Consumer(callbacks=[], async_callbacks=[])
    logs.subscribe(listener)

    entry = logs.add(message("hello"))

    assert listener.queue.get_nowait() == entry


def test_the_snapshot_has_every_entry_kept_oldest_first():
    logs = LogHistory(max_entries=10)
    logs.add(message("one"))
    logs.add(message("two", level="error"))

    snapshot = logs.snapshot()
    assert snapshot["seq"] == 2
    assert snapshot["max_entries"] == 10
    assert [(e["seq"], e["message"], e["level"]) for e in snapshot["entries"]] == [
        (1, "one", "info"),
        (2, "two", "error"),
    ]


# -------------------------------------------------------------- endpoint
def test_the_history_is_served():
    logs = LogHistory()
    logs.add(message("one"))
    server = APIServer()
    logs._register_endpoints(server)

    response = TestClient(server.app).get("/logs/history")

    assert response.status_code == 200
    assert response.json()["data"] == logs.snapshot()


# -------------------------------------------------------------- the component
@pytest.mark.asyncio
async def test_it_stores_what_it_is_sent_and_streams_it():
    source = Log()
    logs = LogHistory(source)
    await logs.setup()
    listener = Consumer(callbacks=[], async_callbacks=[])
    logs.subscribe(listener)
    running = asyncio.create_task(logs.run(experiment=None))

    source.send("hello", level="debug")
    entry = await asyncio.wait_for(listener.queue.get(), timeout=2)
    await logs.shutdown()
    await asyncio.wait_for(running, timeout=2)

    assert entry["message"] == "hello" and entry["level"] == "debug"
    assert list(logs.entries) == [entry]


def test_it_does_not_listen_until_it_is_set_up():
    # So that an experiment made and never run leaves nothing filling up.
    source = Log()
    LogHistory(source)

    assert source._subscribers == []


@pytest.mark.asyncio
async def test_it_catches_up_on_what_was_logged_since_it_was_made():
    source = Log()
    source.send("before")
    logs = LogHistory(source)
    source.send("between one")
    source.send("between two", level="warning")

    await logs.setup()
    source.send("after")

    assert [e["message"] for e in logs.entries] == ["between one", "between two"]
    assert logs.queue.get_nowait()["message"] == "after"
    assert logs in source._subscribers


@pytest.mark.asyncio
async def test_it_stops_listening_when_it_finishes():
    source = Log()
    logs = LogHistory(source)
    await logs.setup()

    await logs.teardown()

    assert logs not in source._subscribers


# -------------------------------------------------------------- the logger
def test_an_exception_is_broadcast_like_any_other_message():
    listener = Consumer(callbacks=[], async_callbacks=[])
    logger.subscribe(listener)
    level = logger._gui_level
    logger._gui_level = "DEBUG"
    try:
        logger.exception("it broke")
    finally:
        logger._gui_level = level
        logger.unsubscribe(listener)

    sent = listener.queue.get_nowait()
    assert sent["message"] == "it broke" and sent["level"] == "exception"


def test_the_logger_keeps_its_recent_messages_numbered():
    level = logger._gui_level
    logger._gui_level = "DEBUG"
    try:
        start = logger.sent
        logger.info("first recent")
        logger.debug("second recent")
    finally:
        logger._gui_level = level

    assert logger.sent == start + 2
    assert [m["message"] for m in logger.recent_since(start)] == [
        "first recent",
        "second recent",
    ]
    assert [m["message"] for m in logger.recent_since(start + 1)] == ["second recent"]


# -------------------------------------------------------------- in an experiment
@pytest.mark.asyncio
async def test_an_experiment_keeps_its_logs_from_the_start_and_streams_new_ones(
    tmp_path,
):
    from aiohttp import ClientSession

    from pyacquisition import Experiment

    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]

    experiment = Experiment(root_path=str(tmp_path), gui=False, api_server_port=port)
    running = asyncio.create_task(experiment._run())
    base = f"http://localhost:{port}"
    try:
        async with ClientSession() as session:
            for _ in range(100):
                try:
                    async with session.get(f"{base}/ping"):
                        break
                except OSError:
                    await asyncio.sleep(0.05)

            async with session.ws_connect(f"ws://localhost:{port}/stream/logs") as ws:
                async with session.get(f"{base}/logs/history") as response:
                    snapshot = (await response.json())["data"]
                logger.warning("a message for the test")
                while (entry := await asyncio.wait_for(ws.receive_json(), 5))[
                    "message"
                ] != "a message for the test":
                    pass

        # Logged while the experiment was being made, before anything connected.
        messages = [e["message"] for e in snapshot["entries"]]
        assert any(m.startswith("Logging configured") for m in messages)
        assert "[Experiment] Fully initialized" in messages
        assert entry["level"] == "warning"
        assert entry["seq"] > snapshot["seq"]
    finally:
        experiment._shutdown_event.set()
        await asyncio.wait_for(running, timeout=20)

    assert experiment._log_history not in logger._subscribers


def test_an_experiment_that_never_runs_leaves_the_logger_alone(tmp_path):
    from pyacquisition import Experiment

    experiment = Experiment(root_path=str(tmp_path), gui=False)

    assert experiment._log_history not in logger._subscribers
