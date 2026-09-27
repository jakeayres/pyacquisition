"""The setup server (`pyacquisition new`): its endpoints, its port, and handing
its window over to the experiment that Run starts."""

import asyncio
import json
import os
import socket
import threading
import time
import urllib.request
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pyacquisition.core import setup
from pyacquisition.core.setup import SETUP_PAGE, SetupServer
from pyacquisition.gui import Gui


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


# ------------------------------------------------------------------ the endpoints
def test_the_config_is_the_files(tmp_path):
    config = write(tmp_path / "rig.toml", '[rack]\nperiod = 0.5\n')

    data = TestClient(SetupServer(config).app).get("/setup/config").json()["data"]

    assert data == {
        "path": str(config.resolve()),
        "exists": True,
        "config": {"rack": {"period": 0.5}},
        "error": None,
    }


def test_a_file_that_does_not_exist_has_no_config(tmp_path):
    data = TestClient(SetupServer(tmp_path / "new.toml").app).get("/setup/config")

    assert data.json()["data"]["exists"] is False
    assert data.json()["data"]["config"] == {}


def test_why_the_last_run_failed_is_given(tmp_path):
    config = write(tmp_path / "rig.toml", "")
    server = SetupServer(config, error="`period` must be a number")

    data = TestClient(server.app).get("/setup/config").json()["data"]

    assert data["error"] == "`period` must be a number"


def test_the_root_goes_to_the_setup_page(tmp_path):
    client = TestClient(SetupServer(write(tmp_path / "rig.toml", "")).app)

    response = client.get("/", follow_redirects=False)
    assert response.headers["location"] == SETUP_PAGE

    page = client.get(SETUP_PAGE)
    assert page.status_code == 200
    assert "js/setup/main.js" in page.text


def test_it_answers_pings_as_the_experiment_does(tmp_path):
    client = TestClient(SetupServer(write(tmp_path / "rig.toml", "")).app)

    assert client.get("/ping").json() == "pong"


def test_there_is_no_experiment_behind_it(tmp_path):
    # The page tells the experiment from the setup server by this.
    client = TestClient(SetupServer(write(tmp_path / "rig.toml", "")).app)

    assert client.get("/experiment/info").status_code == 404


# ------------------------------------------------------------------ the port
def test_the_port_is_the_files(tmp_path):
    config = write(
        tmp_path / "rig.toml", "[api_server]\nport = 8765\nfallback_ports = [8766]\n"
    )

    server = SetupServer(config)

    assert server.port == 8765
    assert server._api_server.fallback_ports == (8766,)


def test_the_port_is_8000_by_default(tmp_path):
    assert SetupServer(write(tmp_path / "rig.toml", "")).port == 8000


def test_a_port_given_wins_over_the_files(tmp_path):
    config = write(tmp_path / "rig.toml", "[api_server]\nport = 8765\n")

    assert SetupServer(config, port=8123).port == 8123


@pytest.mark.parametrize(
    "text",
    [
        "this is not TOML",
        '[api_server]\nport = "eight thousand"\n',
        "[api_server]\nprot = 8765\n",
    ],
)
def test_a_file_whose_port_cant_be_read_gets_the_default(tmp_path, text):
    assert SetupServer(write(tmp_path / "rig.toml", text)).port == 8000


def test_a_taken_port_falls_back_as_the_experiment_does(tmp_path):
    taken, fallback = free_port(), free_port()
    config = write(
        tmp_path / "rig.toml",
        f"[api_server]\nport = {taken}\nfallback_ports = [{fallback}]\n",
    )
    with socket.socket() as holder:
        holder.bind(("localhost", taken))
        server = SetupServer(config)
        try:
            assert server.bind() == fallback
        finally:
            server._api_server.release()


# ------------------------------------------------------------------ stopping
class FakeGui:
    def __init__(self):
        self.handing_over = False

    def start_handover(self):
        self.handing_over = True


def serving(server, window=None):
    """Runs the server in a thread, and hands back the thread once it answers."""
    server.bind()
    thread = threading.Thread(target=lambda: asyncio.run(server.serve(window)))
    thread.start()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{server.port}/ping", timeout=1)
            return thread
        except OSError:
            time.sleep(0.05)
    raise AssertionError("the setup server never answered")


def call(server, path, method="GET"):
    request = urllib.request.Request(f"http://localhost:{server.port}{path}", method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def test_run_hands_the_window_over_and_stops(tmp_path):
    gui = FakeGui()
    server = SetupServer(write(tmp_path / "rig.toml", ""), port=free_port(), gui=gui)
    thread = serving(server)

    answer = call(server, "/setup/run", method="POST")
    thread.join(timeout=10)

    assert answer["data"] == {"port": server.port}  # where the experiment will be
    assert gui.handing_over
    assert not thread.is_alive()
    assert server.run_asked


def test_run_forgets_the_last_failure(tmp_path):
    server = SetupServer(
        write(tmp_path / "rig.toml", ""), port=free_port(), error="it failed"
    )
    thread = serving(server)

    call(server, "/setup/run", method="POST")
    thread.join(timeout=10)

    assert server.error is None  # so the page can tell when a new one comes


def test_shutdown_stops_it_without_running(tmp_path):
    gui = FakeGui()
    server = SetupServer(write(tmp_path / "rig.toml", ""), port=free_port(), gui=gui)
    thread = serving(server)

    call(server, "/setup/shutdown")
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert not server.run_asked
    assert not gui.handing_over


def test_it_stops_when_its_window_closes(tmp_path):
    window = SimpleNamespace(alive=True, is_alive=lambda: window.alive)
    server = SetupServer(write(tmp_path / "rig.toml", ""), port=free_port())
    thread = serving(server, window)

    window.alive = False
    thread.join(timeout=10)

    assert not thread.is_alive()
    assert not server.run_asked


# ------------------------------------------------------------------ handing over
REPORT = "PYACQUISITION_TEST_SETUP_REPORT"


def get(url):
    with urllib.request.urlopen(url, timeout=2) as response:
        return json.load(response)


def wait_for(check, timeout=30.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except OSError:
            pass
        time.sleep(0.1)
    raise TimeoutError


def scripted_window(server, told_to_close, address, handing_over, page="/ui/"):
    """Stands in for the window's process (`gui.window.main`), with no window: it
    presses Run on the setup page, follows the handover, reports what it saw to
    the file named in the environment, and then goes, as a window closing does."""
    report = {"page": page}
    try:
        where = lambda: address.value.decode()  # noqa: E731
        report["setup"] = wait_for(lambda: get(f"{where()}/setup/config"))["data"]
        run = urllib.request.Request(f"{where()}/setup/run", method="POST")
        with urllib.request.urlopen(run, timeout=5) as response:
            report["port"] = json.load(response)["data"]["port"]
        report["handing_over"] = bool(handing_over.value)

        def settled():
            if handing_over.value:
                return None
            try:
                return {"experiment": get(f"{where()}/experiment/info")["data"]}
            except urllib.error.HTTPError:  # the setup server, back again
                return {"setup": get(f"{where()}/setup/config")["data"]}

        report["after"] = wait_for(settled)
        report["address"] = where()
    except Exception as e:  # noqa: BLE001 - reported, for the test to show
        report["failure"] = repr(e)
    with open(os.environ[REPORT], "w", encoding="utf-8") as file:
        json.dump(report, file)


def open_setup_scripted(monkeypatch, tmp_path, config, port):
    from pyacquisition.gui import window

    report = tmp_path / "report.json"
    monkeypatch.setenv(REPORT, str(report))
    monkeypatch.setattr(window, "main", scripted_window)
    thread = threading.Thread(target=setup.open_setup, args=(config, port))
    thread.start()
    thread.join(timeout=60)
    assert not thread.is_alive(), "open_setup never finished"
    return json.loads(report.read_text(encoding="utf-8"))


def test_run_hands_the_window_to_the_experiment(monkeypatch, tmp_path):
    port = free_port()
    config = write(
        tmp_path / "rig.toml",
        f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n\n'
        '[instruments.clock]\ninstrument = "Clock"\n\n'
        '[measurements.t]\ninstrument = "clock"\nmethod = "timestamp_ms"\n',
    )

    report = open_setup_scripted(monkeypatch, tmp_path, config, port)

    assert "failure" not in report, report
    assert report["page"] == SETUP_PAGE
    assert report["setup"]["path"] == str(config.resolve())
    assert report["port"] == port
    assert report["handing_over"]
    assert report["after"] == {"experiment": {"name": "rig"}}
    assert report["address"] == f"http://localhost:{port}"  # the same port


def test_an_experiment_that_fails_to_start_brings_the_setup_page_back(
    monkeypatch, tmp_path
):
    port = free_port()
    config = write(
        tmp_path / "rig.toml",
        f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n\n'
        '[rack]\nperiod = "fast"\n',
    )

    report = open_setup_scripted(monkeypatch, tmp_path, config, port)

    assert "failure" not in report, report
    assert "period" in report["after"]["setup"]["error"]
    assert report["address"] == f"http://localhost:{port}"


def test_the_setup_window_is_the_one_gui_makes(tmp_path):
    gui = Gui(page=SETUP_PAGE)

    process = gui.run_in_new_process()

    assert process._kwargs == {"page": SETUP_PAGE}
