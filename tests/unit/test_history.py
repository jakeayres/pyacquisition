"""The history: rows kept in memory for the GUI, and streamed with a number
for each event, so a client can merge a snapshot with the stream."""

import asyncio
import json
import math
import struct
from enum import Enum

import pytest
from fastapi.testclient import TestClient

from pyacquisition.core.api_server import APIServer
from pyacquisition.core.consumer import Consumer
from pyacquisition.core.history import History

NAN = float("nan")


def same(a, b) -> bool:
    """Equal, with NaN equal to NaN."""
    return len(a) == len(b) and all(
        (math.isnan(x) and math.isnan(y)) or x == y for x, y in zip(a, b)
    )


def columns(segment) -> dict:
    return {name: list(column) for name, column in segment.columns.items()}


# -------------------------------------------------------------- rows
def test_rows_are_kept_column_by_column():
    history = History()
    history.new_file("00.00 start.data")
    history.add_row({"time": 1.0, "T": 4.2})
    history.add_row({"time": 2.0, "T": 4.3})

    assert history.current.file == "00.00 start.data"
    assert history.current.rows == 2
    assert columns(history.current) == {"time": [1.0, 2.0], "T": [4.2, 4.3]}


def test_every_event_gets_the_next_number():
    history = History()

    assert history.new_file("a")["seq"] == 1
    assert history.add_row({"x": 1})["seq"] == 2
    assert history.add_row({"x": 2})["seq"] == 3
    assert history.seq == 3


def test_a_column_that_appears_late_is_nan_before_it():
    history = History()
    history.add_row({"time": 1.0})
    history.add_row({"time": 2.0, "T": 4.2})

    assert same(history.current.columns["T"], [NAN, 4.2])


def test_a_missing_value_is_nan():
    history = History()
    history.add_row({"time": 1.0, "T": 4.2})
    history.add_row({"time": 2.0})

    assert same(history.current.columns["T"], [4.2, NAN])


class Channel(Enum):
    A = "A"


def test_values_that_are_not_numbers_are_kept_as_the_latest_only():
    history = History()
    history.add_row({"time": 1.0, "channel": Channel.A, "note": "cooling"})

    assert set(history.current.columns) == {"time"}
    assert history.latest == {"time": 1.0, "channel": "A", "note": "cooling"}


def test_a_bool_is_a_number_and_an_int_is_a_float():
    history = History()
    history.add_row({"on": True, "count": 3})

    assert columns(history.current) == {"on": [1.0], "count": [3.0]}


def test_a_numeric_column_is_nan_where_a_value_is_not_a_number():
    history = History()
    history.add_row({"T": 4.2})
    history.add_row({"T": "overload"})

    assert same(history.current.columns["T"], [4.2, NAN])
    assert history.latest["T"] == "overload"


def test_a_row_is_streamed_as_json():
    history = History()

    event = history.add_row({"T": NAN, "x": 1.5, "channel": Channel.A, "none": None})

    assert event == {
        "type": "row",
        "seq": 1,
        "values": {"T": None, "x": 1.5, "channel": "A", "none": None},
    }
    json.dumps(event, allow_nan=False)  # valid JSON, which NaN is not


# -------------------------------------------------------------- files
def test_a_new_file_moves_the_current_segment_to_previous():
    history = History()
    history.new_file("00.00 start.data")
    history.add_row({"x": 1.0})
    history.new_file("00.01 sweep.data")
    history.add_row({"x": 2.0})

    assert history.previous.file == "00.00 start.data"
    assert columns(history.previous) == {"x": [1.0]}
    assert history.current.file == "00.01 sweep.data"
    assert columns(history.current) == {"x": [2.0]}


def test_only_one_previous_file_is_kept():
    history = History()
    for n in range(3):
        history.new_file(f"file {n}")
        history.add_row({"x": float(n)})

    assert history.previous.file == "file 1"
    assert history.current.file == "file 2"


def test_two_new_files_in_a_row_keep_the_previous_one_with_data():
    # The second new file comes before any row of the first, so the first is only
    # renamed, and the file with data stays as the previous one.
    history = History()
    history.new_file("with data")
    history.add_row({"x": 1.0})
    history.new_file("empty")
    history.new_file("next")

    assert history.previous.file == "with data"
    assert history.current.file == "next"
    assert history.current.rows == 0


def test_the_first_file_names_the_empty_current_segment():
    history = History()
    history.new_file("00.00 start.data")

    assert history.previous is None
    assert history.current.file == "00.00 start.data"


# -------------------------------------------------------------- the limit
def total_rows(history) -> int:
    return sum(s.rows for s in (history.previous, history.current) if s)


def test_there_are_never_more_rows_than_the_limit():
    history = History(max_rows=100)
    for n in range(1000):
        history.add_row({"x": float(n)})
        assert total_rows(history) <= 100

    assert history.current.columns["x"][-1] == 999.0  # the newest are kept


def test_the_oldest_rows_are_dropped_in_batches_of_one_percent():
    history = History(max_rows=1000)
    for n in range(1001):
        history.add_row({"x": float(n)})

    assert total_rows(history) == 990
    assert history.current.columns["x"][0] == 11.0


def test_the_previous_file_is_dropped_from_first():
    history = History(max_rows=100)
    history.new_file("old")
    for n in range(60):
        history.add_row({"x": float(n)})
    history.new_file("new")
    for n in range(50):
        history.add_row({"x": 100.0 + n})

    assert history.current.rows == 50  # untouched
    assert total_rows(history) <= 100
    # The 10 dropped as the new rows came in are the previous file's oldest.
    assert list(history.previous.columns["x"]) == [float(n) for n in range(10, 60)]


def test_the_previous_file_goes_once_it_is_empty():
    history = History(max_rows=100)
    history.new_file("old")
    history.add_row({"x": 0.0})
    history.new_file("new")
    for n in range(100):
        history.add_row({"x": float(n)})

    assert history.previous is None
    assert total_rows(history) <= 100


# -------------------------------------------------------------- snapshots
def filled_history() -> History:
    history = History()
    history.new_file("old")
    history.add_row({"time": 1.0, "T": 4.2, "channel": Channel.A})
    history.new_file("new")
    history.add_row({"time": 2.0, "T": NAN})
    history.add_row({"time": 3.0, "T": 4.4, "x": 7.0})
    return history


def test_the_json_snapshot_has_every_segment_with_null_for_nan():
    snapshot = filled_history().snapshot_json()

    assert snapshot == {
        "seq": 5,
        "max_rows": 500_000,
        "latest": {"time": 3.0, "T": 4.4, "channel": "A", "x": 7.0},
        "segments": [
            {"file": "old", "rows": 1, "columns": {"time": [1.0], "T": [4.2]}},
            {
                "file": "new",
                "rows": 2,
                "columns": {"time": [2.0, 3.0], "T": [None, 4.4], "x": [None, 7.0]},
            },
        ],
    }
    json.dumps(snapshot, allow_nan=False)


def decode_binary(data: bytes) -> dict:
    """How a client reads the binary snapshot (see History.snapshot_binary)."""
    (length,) = struct.unpack_from("<I", data)
    assert (4 + length) % 8 == 0  # the columns start 8-byte aligned
    header = json.loads(data[4 : 4 + length])
    offset = 4 + length
    for segment in header["segments"]:
        values = {}
        for name in segment["columns"]:
            values[name] = list(
                struct.unpack_from(f"<{segment['rows']}d", data, offset)
            )
            offset += 8 * segment["rows"]
        segment["columns"] = values
    assert offset == len(data)
    return header


def test_the_binary_snapshot_holds_the_same_as_the_json_one():
    history = filled_history()
    decoded = decode_binary(history.snapshot_binary())
    expected = history.snapshot_json()

    assert decoded["seq"] == expected["seq"]
    assert decoded["latest"] == expected["latest"]
    for got, want in zip(decoded["segments"], expected["segments"]):
        assert (got["file"], got["rows"]) == (want["file"], want["rows"])
        for name, column in want["columns"].items():
            wanted = [NAN if v is None else v for v in column]
            assert same(got["columns"][name], wanted)


def test_an_empty_history_has_an_empty_snapshot():
    history = History()

    assert decode_binary(history.snapshot_binary())["segments"] == [
        {"file": None, "rows": 0, "columns": {}}
    ]
    assert history.info() == {
        "seq": 0,
        "max_rows": 500_000,
        "segments": [{"file": None, "rows": 0, "columns": []}],
    }


# -------------------------------------------------------------- merging
class Client:
    """A client following the protocol in history.py: a snapshot, then events."""

    def __init__(self, snapshot):
        self.seq = snapshot["seq"]
        self.segments = [
            {
                "file": s["file"],
                "columns": {k: list(v) for k, v in s["columns"].items()},
            }
            for s in snapshot["segments"]
        ]

    def apply(self, event):
        if event["seq"] <= self.seq:
            return  # already in the snapshot
        assert event["seq"] == self.seq + 1, "an event was missed"
        self.seq = event["seq"]
        current = self.segments[-1]
        if event["type"] == "new_file":
            if any(current["columns"].values()):
                self.segments = [current, {"file": event["file"], "columns": {}}]
            else:
                current["file"] = event["file"]
            return
        rows = len(next(iter(current["columns"].values()), []))
        numbers = {
            k: v for k, v in event["values"].items() if isinstance(v, (int, float))
        }
        # A null is a number that is missing, in a column that already has numbers.
        for name, column in current["columns"].items():
            column.append(numbers.get(name))
        for name in numbers.keys() - current["columns"].keys():
            current["columns"][name] = [None] * rows + [numbers[name]]


def test_a_snapshot_taken_part_way_merges_with_the_stream_exactly():
    history = History(max_rows=10_000)
    listener = Consumer(callbacks=[], async_callbacks=[])
    history.subscribe(listener)  # connected to the stream before the snapshot

    history.new_file("first")
    for n in range(5):
        history.add_row({"time": float(n), "T": 4.0 + n})
    snapshot = history.snapshot_json()  # part way
    for n in range(5, 8):
        history.add_row({"time": float(n), "T": NAN})
    history.new_file("second")
    history.new_file("third")  # before any row, so it only renames
    for n in range(8, 12):
        history.add_row({"time": float(n), "T": 4.0 + n, "x": 1.0})

    client = Client(snapshot)
    while not listener.queue.empty():
        client.apply(listener.queue.get_nowait())

    final = history.snapshot_json()
    assert client.seq == final["seq"]
    assert client.segments == [
        {"file": s["file"], "columns": s["columns"]} for s in final["segments"]
    ]


# -------------------------------------------------------------- endpoints
@pytest.fixture
def client():
    history = filled_history()
    server = APIServer()
    history._register_endpoints(server)
    return TestClient(server.app)


def test_history_is_served_as_json(client):
    response = client.get("/history")

    assert response.status_code == 200
    assert response.json()["data"] == filled_history().snapshot_json()


def test_history_is_served_as_binary(client):
    response = client.get("/history", params={"format": "binary"})

    assert response.headers["content-type"] == "application/octet-stream"
    assert decode_binary(response.content)["seq"] == 5


def test_an_empty_history_is_served_as_valid_json():
    server = APIServer()
    History()._register_endpoints(server)

    assert TestClient(server.app).get("/history").json()["data"] == {
        "seq": 0,
        "max_rows": 500_000,
        "latest": {},
        "segments": [{"file": None, "rows": 0, "columns": {}}],
    }


def test_a_long_column_is_served_whole_as_json():
    # Longer than the pieces the JSON is sent in, with NaN in several of them.
    history = History()
    values = [float("nan") if n % 7000 == 0 else float(n) for n in range(50_000)]
    for value in values:
        history.add_row({"x": value})
    server = APIServer()
    history._register_endpoints(server)

    column = TestClient(server.app).get("/history").json()["data"]["segments"][0]
    assert column["columns"]["x"] == [None if math.isnan(v) else v for v in values]


def test_an_unknown_format_is_refused(client):
    assert client.get("/history", params={"format": "csv"}).status_code == 422


def test_history_info_describes_it_without_the_data(client):
    assert client.get("/history/info").json()["data"] == {
        "seq": 5,
        "max_rows": 500_000,
        "segments": [
            {"file": "old", "rows": 1, "columns": ["time", "T"]},
            {"file": "new", "rows": 2, "columns": ["time", "T", "x"]},
        ],
    }


# -------------------------------------------------------------- the scribe's files
@pytest.mark.asyncio
async def test_the_scribe_tells_listeners_of_each_file(tmp_path):
    from pyacquisition.core.scribe import Scribe

    scribe = Scribe(root_path=tmp_path)
    files = []
    scribe.add_file_listener(files.append)

    await scribe.setup()
    scribe.next_file("sweep")
    scribe.next_file("cooldown", next_block=True)

    assert files == ["00.00 start.data", "00.01 sweep.data", "01.00 cooldown.data"]


@pytest.mark.asyncio
async def test_a_failing_listener_does_not_stop_the_scribe(tmp_path):
    from pyacquisition.core.scribe import Scribe

    scribe = Scribe(root_path=tmp_path)
    files = []

    def broken(file):
        raise RuntimeError("broken")

    scribe.add_file_listener(broken)
    scribe.add_file_listener(files.append)
    await scribe.setup()

    assert files == ["00.00 start.data"]


# -------------------------------------------------------------- the component
@pytest.mark.asyncio
async def test_it_stores_the_rows_it_is_sent_and_streams_them():
    history = History()
    listener = Consumer(callbacks=[], async_callbacks=[])
    history.subscribe(listener)
    running = asyncio.create_task(history.run(experiment=None))

    await history.queue.put({"x": 1.0})
    event = await asyncio.wait_for(listener.queue.get(), timeout=2)
    await history.shutdown()
    await asyncio.wait_for(running, timeout=2)

    assert event == {"type": "row", "seq": 1, "values": {"x": 1.0}}
    assert columns(history.current) == {"x": [1.0]}


# -------------------------------------------------------------- in an experiment
def test_the_limit_is_the_history_points_option(tmp_path):
    from pyacquisition import Experiment

    config = tmp_path / "rig.toml"
    config.write_text(
        f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n'
        "[data]\nhistory_points = 2000\n[gui]\nrun = false\n"
    )

    assert Experiment.from_config(str(config))._history.max_rows == 2000
    assert Experiment(root_path=str(tmp_path), gui=False)._history.max_rows == 500_000


@pytest.mark.asyncio
async def test_an_experiment_keeps_and_streams_its_rows_and_files(tmp_path):
    import socket

    from aiohttp import ClientSession

    from pyacquisition import Experiment, Measurement
    from pyacquisition.instruments import Clock

    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]

    class Rig(Experiment):
        def setup(self):
            clock = Clock("clock")
            self.add_instrument(clock)
            self.add_measurement(Measurement("time", clock.time))
            self.add_calculation(lambda row: {"double": 2 * row["time"]})

    experiment = Rig(
        root_path=str(tmp_path),
        gui=False,
        api_server_port=port,
        measurement_period=0.05,
    )
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

            async with session.ws_connect(f"ws://localhost:{port}/stream/data") as ws:
                row = await asyncio.wait_for(ws.receive_json(), timeout=5)
                assert row["type"] == "row"
                assert set(row["values"]) == {"time", "double"}  # calculated too

                async with session.get(f"{base}/scribe/next_file?title=sweep"):
                    pass
                while (event := await asyncio.wait_for(ws.receive_json(), 5))[
                    "type"
                ] != "new_file":
                    pass
                assert event["file"] == "00.01 sweep.data"

            await asyncio.sleep(0.3)
            async with session.get(f"{base}/history") as response:
                snapshot = (await response.json())["data"]

        old, new = snapshot["segments"]
        assert old["file"] == "00.00 start.data" and old["rows"] > 0
        assert new["file"] == "00.01 sweep.data" and new["rows"] > 0
        assert list(new["columns"]) == ["time", "double"]
    finally:
        experiment._shutdown_event.set()
        await asyncio.wait_for(running, timeout=20)
