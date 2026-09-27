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


# ------------------------------------------------------------ describing, checking, saving
def client_for(tmp_path, text="# mine\n[rack]\nperiod = 0.5  # fast\n"):
    config = tmp_path / "rig.toml"
    if text is not None:
        config.write_bytes(text.encode("utf-8"))  # its line endings as they are
    return TestClient(SetupServer(config).app), config


def test_what_a_config_can_hold_is_described(tmp_path):
    client, _ = client_for(tmp_path)

    data = client.get("/setup/describe").json()["data"]

    assert {o["name"] for o in data["options"]} >= {"measurement_period", "root_path"}
    drivers = {d["name"]: d for d in data["drivers"]}
    assert drivers["Clock"]["hardware"] is False
    assert drivers["SR_830"]["hardware"] is True
    assert {"name": "timestamp_ms", "doc": drivers["Clock"]["queries"][-1]["doc"]} in drivers[
        "Clock"
    ]["queries"]
    ips = {q["name"] for q in drivers["Mercury_IPS"]["queries"]}
    assert "get_output_field" in ips and "to_zero" not in ips  # a command
    assert data["calculations"] == [
        {"name": "Sum", "keys": {"inputs": "columns"}},
        {"name": "RollingMean", "keys": {"column": "column", "window": "count"}},
    ]
    assert data["adapters"] == ["pyvisa", "mock", "prologix", "record"]


def test_a_config_is_checked_with_what_it_would_write(tmp_path):
    client, _ = client_for(tmp_path)

    data = client.post("/setup/check", json={"rack": {"period": 0.25}}).json()["data"]

    assert data == {"problems": [], "toml": "# mine\n[rack]\nperiod = 0.25  # fast\n"}


def test_a_config_with_problems_says_where_they_are(tmp_path):
    client, _ = client_for(tmp_path)

    data = client.post("/setup/check", json={"rack": {"period": -1}}).json()["data"]

    assert data["problems"] == [
        {"where": ["rack", "period"], "message": "`period` must be a positive number, got -1"}
    ]
    assert "period = -1" in data["toml"]  # the preview still follows


def test_a_new_file_is_previewed_with_its_header(tmp_path):
    client, _ = client_for(tmp_path, text=None)

    data = client.post("/setup/check", json={"rack": {"period": 0.5}}).json()["data"]

    assert data["toml"].startswith("# An experiment's config")


def test_saving_writes_the_file_keeping_its_comments(tmp_path):
    client, config = client_for(tmp_path)

    response = client.post("/setup/save", json={"rack": {"period": 1.5}})

    assert response.status_code == 200
    assert config.read_text(encoding="utf-8") == "# mine\n[rack]\nperiod = 1.5  # fast\n"


def test_a_config_with_problems_is_not_saved(tmp_path):
    client, config = client_for(tmp_path)

    response = client.post("/setup/save", json={"rack": {"period": -1}})

    assert response.status_code == 422
    assert response.json()["data"]["problems"][0]["where"] == ["rack", "period"]
    assert "period = 0.5" in config.read_text(encoding="utf-8")


def test_saving_makes_a_file_that_does_not_exist(tmp_path):
    client, config = client_for(tmp_path, text=None)

    assert client.post("/setup/save", json={"rack": {"period": 0.5}}).status_code == 200
    assert "period = 0.5" in config.read_text(encoding="utf-8")


# ------------------------------------------------------------ a driver's query
def test_a_query_route_answers_with_its_args_as_a_config_holds_them(tmp_path):
    client, _ = client_for(tmp_path)

    response = client.get(
        "/setup/drivers/Lakeshore_350/get_temperature", params={"input_channel": "Input A"}
    )

    assert response.json()["data"] == {"input_channel": "INPUT_A"}  # by name


def test_a_query_route_checks_its_args(tmp_path):
    client, _ = client_for(tmp_path)

    assert (
        client.get(
            "/setup/drivers/Lakeshore_350/get_temperature", params={"input_channel": "nope"}
        ).status_code
        == 422
    )


def test_a_query_route_refuses_an_enum_by_its_argument(tmp_path):
    client, _ = client_for(tmp_path)

    response = client.get(
        "/setup/drivers/Lakeshore_350/get_temperature", params={"input_channel": "INPUT_Z"}
    )

    (problem,) = response.json()["detail"]
    assert problem["loc"] == ["query", "input_channel"]
    assert "INPUT_A, INPUT_B" in problem["msg"]


def test_a_query_route_leaves_out_what_is_not_given(tmp_path):
    client, _ = client_for(tmp_path)

    assert client.get("/setup/drivers/Clock/timestamp_ms").json()["data"] == {}


def test_a_query_routes_schema_is_the_form_the_page_builds(tmp_path):
    client, _ = client_for(tmp_path)

    paths = client.get("/openapi.json").json()["paths"]
    (parameter,) = paths["/setup/drivers/Lakeshore_350/get_temperature"]["get"]["parameters"]

    assert parameter["name"] == "input_channel" and parameter["required"] is True
    # Names, as the file holds them, with the labels to show.
    assert parameter["schema"]["enum"] == ["INPUT_A", "INPUT_B", "INPUT_C", "INPUT_D"]
    assert parameter["schema"]["x-labels"] == ["Input A", "Input B", "Input C", "Input D"]
    assert "/setup/drivers/Mercury_IPS/to_zero" not in paths  # a command


# ------------------------------------------------------------ testing an instrument
def asked(client, instrument="SR_830", adapter="mock", resource="GPIB0::7::INSTR", args=None):
    return client.post(
        "/setup/test",
        json={"instrument": instrument, "adapter": adapter, "resource": resource, "args": args or {}},
    ).json()["data"]


def test_an_instrument_that_answers_as_its_driver_matches(tmp_path):
    client, _ = client_for(tmp_path)

    data = asked(client, args={"responses": {"*IDN?": "Stanford_Research_Systems,SR830,1,1"}})

    assert data == {
        "reply": "Stanford_Research_Systems,SR830,1,1",
        "matches": True,
        "expected": ["STANFORD", "SR830"],
        "missing": [],
        "error": None,
    }


def test_an_instrument_that_answers_as_another_does_not_match(tmp_path):
    client, _ = client_for(tmp_path)

    data = asked(client, args={"responses": {"*IDN?": "LSCI,MODEL350"}})

    assert data["matches"] is False
    assert data["missing"] == ["STANFORD", "SR830"]


def test_a_driver_with_no_identity_can_not_be_matched(tmp_path):
    client, _ = client_for(tmp_path)

    data = asked(client, instrument="Mercury_IPS")

    assert data["reply"]  # it answered, as the mock does
    assert data["matches"] is None and data["expected"] is None


def test_an_address_that_can_not_be_opened_says_why(tmp_path):
    client, _ = client_for(tmp_path)

    data = asked(client, adapter="prologix", resource="NOT_A_PORT::7")

    assert data["reply"] is None and data["matches"] is None
    assert "Could not open 'NOT_A_PORT::7'" in data["error"]


def test_nothing_is_asked_without_an_address(tmp_path):
    client, _ = client_for(tmp_path)

    assert asked(client, resource="")["error"] == "It needs an adapter and an address to test."


def test_the_resource_is_closed_after_asking(tmp_path, monkeypatch):
    from pyacquisition.core import setup as setup_module

    closed = []

    class Resource:
        def query(self, text):
            return "Stanford_Research_Systems,SR830,1,1"

        def close(self):
            closed.append(True)

    monkeypatch.setattr(setup_module, "open_resource", lambda *a, **k: Resource())
    client, _ = client_for(tmp_path)

    assert asked(client)["matches"] is True
    assert closed == [True]
