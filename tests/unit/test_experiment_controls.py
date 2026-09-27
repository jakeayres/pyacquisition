"""What the GUI's top bar needs from the scribe and the rack (milestone 8)."""

import pytest
from fastapi.testclient import TestClient

from pyacquisition.core.api_server import APIServer
from pyacquisition.core.rack import Rack
from pyacquisition.core.scribe import Scribe, title_problem


@pytest.fixture
def scribe(tmp_path):
    return Scribe(root_path=tmp_path)


def serve(component):
    server = APIServer()
    component._register_endpoints(server)
    return TestClient(server.app)


# -------------------------------------------------------------- the scribe
def test_the_state_names_the_file_and_the_next_ones(scribe, tmp_path):
    scribe.next_file("sweep")

    assert scribe.state() == {
        "directory": str(tmp_path),
        "file": "00.01 sweep.data",
        "block": "00",
        "step": "01",
        "title": "sweep",
        "extension": "data",
        "next_step": "00.02 {title}.data",
        "next_block": "01.00 {title}.data",
    }


def test_the_next_names_are_the_names_next_file_gives(scribe):
    for next_block in (False, True):
        expected = scribe.state()["next_block" if next_block else "next_step"]
        scribe.next_file("cooldown", next_block=next_block)
        assert scribe.current_file() == expected.format(title="cooldown")


def test_the_state_is_served(scribe):
    response = serve(scribe).get("/scribe/state")

    assert response.status_code == 200
    assert response.json()["data"] == scribe.state()


def test_a_new_file_is_started_through_the_api(scribe):
    client = serve(scribe)

    response = client.get("/scribe/next_file", params={"title": "cooldown", "next_block": True})

    assert response.status_code == 200
    assert scribe.current_file() == "01.00 cooldown.data"


@pytest.mark.parametrize("title", ["", "   ", "a/b", "a:b", 'say "hi"', "why?", "tab\there"])
def test_a_title_that_cannot_be_a_file_name_is_refused(scribe, title):
    response = serve(scribe).get("/scribe/next_file", params={"title": title})

    assert response.status_code == 422
    assert response.json()["detail"] == title_problem(title)
    assert scribe.current_file() == "00.00 start.data"  # unchanged


def test_what_is_wrong_with_a_title_is_said_plainly():
    assert title_problem("sweep up 2") is None
    assert title_problem("4.2 K") is None
    assert title_problem("") == "The title is empty."
    assert title_problem("a/b:c") == "A title can't contain / :"


# -------------------------------------------------------------- the rack
def test_the_period_is_set_through_the_api():
    rack = Rack(period=0.25)

    response = serve(rack).get("/rack/period/set/", params={"period": 0.5})

    assert response.status_code == 200
    assert rack.period == 0.5
    assert serve(rack).get("/rack/state").json()["period"] == 0.5


@pytest.mark.parametrize("period", [0, -1])
def test_a_period_that_is_not_above_zero_is_refused(period):
    rack = Rack(period=0.25)

    response = serve(rack).get("/rack/period/set/", params={"period": period})

    assert response.status_code == 422
    assert rack.period == 0.25


def test_pausing_and_resuming_show_in_the_state():
    rack = Rack()
    client = serve(rack)

    client.get("/rack/pause/")
    assert client.get("/rack/state").json()["paused"] is True
    client.get("/rack/resume/")
    assert client.get("/rack/state").json()["paused"] is False


def test_a_relative_data_folder_is_given_in_full(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    scribe = Scribe(root_path="my_data")

    assert scribe.current_directory() == str(tmp_path / "my_data")
    assert scribe.state()["directory"] == str(tmp_path / "my_data")


# -------------------------------------------------------------- the loop time
async def run_rack(rack, seconds):
    import asyncio

    task = asyncio.create_task(rack.run())
    await asyncio.sleep(seconds)
    task.cancel()


@pytest.mark.asyncio
async def test_the_loop_time_is_the_period_while_measuring_keeps_up():
    # Periods well above Windows' timer resolution (15.6 ms), which a shorter
    # sleep is rounded up to.
    rack = Rack(period=0.1)
    assert rack.loop_time is None  # nothing has run

    await run_rack(rack, 0.65)

    assert rack.loop_time == pytest.approx(0.1, abs=0.02)
    assert serve(rack).get("/rack/state").json()["loop_time"] == rack.loop_time


@pytest.mark.asyncio
async def test_the_loop_time_is_longer_when_measuring_is_slower_than_the_period():
    import time

    from pyacquisition.core.measurement import Measurement

    rack = Rack(period=0.05)
    rack.measurements["slow"] = Measurement("slow", lambda: time.sleep(0.15) or 1.0)

    await run_rack(rack, 1.0)

    assert rack.loop_time == pytest.approx(0.15, abs=0.03)


@pytest.mark.asyncio
async def test_pausing_starts_the_loop_time_again():
    rack = Rack(period=0.05)
    await run_rack(rack, 0.2)
    assert rack.loop_time is not None

    rack.pause()

    assert rack.loop_time is None
    assert serve(rack).get("/rack/state").json()["loop_time"] is None
