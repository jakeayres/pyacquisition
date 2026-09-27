"""The new GUI: choosing it, serving its page, and its window and the experiment
living and dying together."""

import asyncio
import pickle
import socket
import time
from multiprocessing import Process

import pytest
from fastapi.testclient import TestClient

from pyacquisition import Experiment
from pyacquisition.gui import Gui
from pyacquisition.new_gui import NewGui
from pyacquisition.new_gui.window import Lifeline


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


# -------------------------------------------------------------- choosing the GUI
@pytest.mark.parametrize(
    "value, kind",
    [
        (True, Gui),
        ("classic", Gui),
        ("new", NewGui),
        ("NEW", NewGui),
        (False, Gui),  # made but not started, as it always has been
    ],
)
def test_the_gui_option_picks_the_gui(tmp_path, value, kind):
    experiment = Experiment(root_path=str(tmp_path), gui=value)

    assert isinstance(experiment._gui, kind)
    assert experiment._run_gui is (value is not False)


@pytest.mark.parametrize("value", ["yes", "modern", 1, 0.5])
def test_an_unknown_gui_is_refused(tmp_path, value):
    class MyExperiment(Experiment):
        root_path = str(tmp_path)
        gui = value

    with pytest.raises(
        ValueError, match="`gui` must be True, False, 'classic' or 'new'"
    ):
        MyExperiment()


def test_the_new_gui_can_be_chosen_in_toml(tmp_path):
    config = tmp_path / "rig.toml"
    config.write_text(
        f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n\n[gui]\nrun = "new"\n'
    )

    experiment = Experiment.from_config(str(config))

    assert isinstance(experiment._gui, NewGui)


def test_the_new_gui_uses_the_api_server_address(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui="new", api_server_port=8123)

    assert experiment._gui.server == "http://localhost:8123"


def test_a_server_on_every_interface_is_reached_through_localhost():
    assert NewGui(host="0.0.0.0", port=9000).server == "http://localhost:9000"


def test_the_new_gui_can_be_sent_to_its_process():
    gui = pickle.loads(pickle.dumps(NewGui(port=8123)))

    assert gui.server == "http://localhost:8123"
    assert gui.run_in_new_process().is_alive() is False  # made, not started


# -------------------------------------------------------------- serving the page
@pytest.fixture(params=[False, "new"])
def client(tmp_path, request):
    """The page is served whichever GUI runs, so it can be opened in a browser."""
    experiment = Experiment(root_path=str(tmp_path), gui=request.param)
    return TestClient(experiment._api_server.app)


def test_the_page_is_served_at_ui(client):
    response = client.get("/ui/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<div id="app">' in response.text


def test_the_root_sends_you_to_the_page(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/ui/"


@pytest.mark.parametrize(
    "path",
    [
        "/ui/js/main.js",
        "/ui/vendor/preact/preact.module.js",
        "/ui/vendor/preact/hooks.module.js",
        "/ui/vendor/htm/htm.module.js",
    ],
)
def test_modules_are_served_as_javascript(client, path):
    # A module served as anything else, such as text/plain, is refused by the
    # browser, and the page stays blank.
    response = client.get(path)

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


@pytest.mark.parametrize("path", ["/ui/", "/ui/js/main.js", "/ui/css/app.css"])
def test_the_browser_checks_the_page_is_current_each_time(client, path):
    # Otherwise the window can run old scripts from its cache after an update.
    response = client.get(path)

    assert response.headers["cache-control"] == "no-cache"
    assert "etag" in response.headers  # so an unchanged file is a quick 304


def test_an_unchanged_file_is_not_sent_again(client):
    etag = client.get("/ui/js/main.js").headers["etag"]

    assert (
        client.get("/ui/js/main.js", headers={"if-none-match": etag}).status_code == 304
    )


def test_the_page_is_not_in_the_api_schema(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert "/" not in paths
    assert not any(path.startswith("/ui") for path in paths)


# -------------------------------------------------------------- the experiment's name
def info(experiment) -> dict:
    experiment._register_endpoints(experiment._api_server)
    client = TestClient(experiment._api_server.app)
    return client.get("/experiment/info").json()["data"]


def test_an_experiment_is_named_after_its_class(tmp_path):
    class CryostatRun(Experiment):
        pass

    assert info(CryostatRun(root_path=str(tmp_path), gui=False)) == {
        "name": "CryostatRun"
    }


def test_a_plain_experiment_from_toml_is_named_after_the_file(tmp_path):
    config = tmp_path / "magnet_sweep.toml"
    config.write_text(f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n')

    assert info(Experiment.from_config(str(config), gui=False)) == {
        "name": "magnet_sweep"
    }


def test_a_subclass_from_toml_keeps_its_class_name(tmp_path):
    class CryostatRun(Experiment):
        pass

    config = tmp_path / "magnet_sweep.toml"
    config.write_text(f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n')

    assert info(CryostatRun.from_config(str(config), gui=False)) == {
        "name": "CryostatRun"
    }


# -------------------------------------------------------------- the window closing itself
class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_the_window_stays_while_the_experiment_answers():
    lifeline = Lifeline(missed=3)

    assert not any(lifeline.record(True) for _ in range(10))


def test_the_window_closes_after_missed_checks_in_a_row():
    lifeline = Lifeline(missed=3)
    lifeline.record(True)

    assert [lifeline.record(False) for _ in range(3)] == [False, False, True]


def test_an_answer_resets_the_missed_checks():
    lifeline = Lifeline(missed=3)
    lifeline.record(True)
    lifeline.record(False)
    lifeline.record(False)
    lifeline.record(True)

    assert [lifeline.record(False) for _ in range(3)] == [False, False, True]


def test_the_window_waits_for_the_experiment_to_start():
    clock = Clock()
    lifeline = Lifeline(missed=3, startup_timeout=60, clock=clock)

    clock.now = 59
    assert not any(lifeline.record(False) for _ in range(10))

    clock.now = 61
    assert lifeline.record(False)


def test_the_window_can_be_told_to_close():
    gui = NewGui(port=8123)
    process = gui.run_in_new_process()
    closing = process._args[1]

    assert not closing.value
    gui.close()
    assert closing.value


def watch_then_leave(flag):
    """As the window does when you close it: watches the flag, then goes by itself."""
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline and not flag.value:
        time.sleep(0.01)


def test_telling_a_window_that_has_gone_to_close_does_not_hang():
    # With a multiprocessing.Event, this hung for ever: setting it waits for each
    # process waiting on it to wake, and a window that has gone never does.
    import threading

    gui = NewGui(port=8123)
    flag = gui.run_in_new_process()._args[1]
    window = Process(target=watch_then_leave, args=(flag,))
    window.start()
    window.join(timeout=10)

    closing = threading.Thread(target=gui.close, daemon=True)
    closing.start()
    closing.join(timeout=2)

    assert not closing.is_alive()


def test_telling_a_gui_that_never_started_to_close_does_nothing():
    NewGui().close()


class FakeWebviewWindow:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


def test_the_window_closes_at_once_when_told(monkeypatch):
    from types import SimpleNamespace

    from pyacquisition.new_gui import window

    pings = []
    monkeypatch.setattr(window, "ping", lambda server: pings.append(1) or True)
    app = window._Window("http://localhost:1")
    app.window = FakeWebviewWindow()

    app.watch(SimpleNamespace(value=True))

    assert app.window.destroyed
    assert len(pings) <= 1  # it did not wait for the experiment to stop answering


def test_the_window_closes_when_the_experiment_stops_answering(monkeypatch):
    from pyacquisition.new_gui import window

    answers = iter([True, False, False, False])
    monkeypatch.setattr(window, "ping", lambda server: next(answers))
    monkeypatch.setattr(window, "PING_PERIOD", 0.01)
    app = window._Window("http://localhost:1")
    app.window = FakeWebviewWindow()

    app.watch()

    assert app.window.destroyed


# -------------------------------------------------------------- the experiment following the GUI
class FakeProcess:
    def __init__(self, alive):
        self.alive = alive

    def is_alive(self):
        return self.alive


@pytest.mark.asyncio
async def test_the_experiment_shuts_down_when_the_gui_process_ends(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    process = FakeProcess(alive=True)
    watcher = asyncio.create_task(experiment._watch_gui(process, period=0.01))

    await asyncio.sleep(0.05)
    assert not experiment._shutdown_event.is_set()

    process.alive = False
    await asyncio.wait_for(watcher, timeout=1)
    assert experiment._shutdown_event.is_set()


@pytest.mark.asyncio
async def test_the_watcher_stops_when_the_experiment_shuts_down(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    watcher = asyncio.create_task(
        experiment._watch_gui(FakeProcess(alive=True), period=10)
    )

    experiment._shutdown_event.set()

    await asyncio.wait_for(watcher, timeout=1)


class ShortLivedGui:
    """A stand-in for a GUI whose process ends by itself after a moment."""

    def run_in_new_process(self):
        return Process(target=time.sleep, args=(0.5,))


def test_a_running_experiment_stops_when_its_gui_process_ends(tmp_path):
    experiment = Experiment(
        root_path=str(tmp_path), gui=False, api_server_port=free_port()
    )
    experiment._run_gui = True
    experiment._gui = ShortLivedGui()

    started = time.monotonic()
    asyncio.run(asyncio.wait_for(experiment._run(), timeout=20))

    assert experiment._shutdown_event.is_set()
    assert not experiment._ui_process.is_alive()
    assert time.monotonic() - started < 15


# -------------------------------------------------------------- the data folder
def test_the_data_folder_is_the_one_the_experiment_names(monkeypatch, tmp_path):
    import io
    import json

    from pyacquisition.new_gui import window

    asked = []

    def urlopen(url, timeout):
        asked.append(url)
        return io.BytesIO(json.dumps({"status": 200, "data": str(tmp_path)}).encode())

    monkeypatch.setattr(window.urllib.request, "urlopen", urlopen)

    assert window.data_folder("http://localhost:8123") == str(tmp_path)
    assert asked == ["http://localhost:8123/scribe/current_directory"]


def test_there_is_no_data_folder_while_the_experiment_does_not_answer():
    from pyacquisition.new_gui import window

    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    assert window.data_folder(f"http://localhost:{port}") is None


def test_a_folder_is_opened_only_if_it_exists(monkeypatch, tmp_path):
    from pyacquisition.new_gui import window

    opened = []
    monkeypatch.setattr(window.sys, "platform", "win32")
    monkeypatch.setattr(window.os, "startfile", opened.append, raising=False)

    assert window.open_folder(str(tmp_path)) is True
    assert window.open_folder(str(tmp_path / "missing")) is False
    assert window.open_folder(None) is False
    assert opened == [str(tmp_path)]


def test_every_file_the_page_is_made_of_is_utf8():
    """A character written in another encoding shows as a replacement mark
    (once, "Load…" showed as "Load�")."""
    from pathlib import Path

    import pyacquisition.new_gui

    static = Path(pyacquisition.new_gui.__file__).parent / "static"
    for path in static.rglob("*"):
        if path.suffix in {".js", ".css", ".html", ".svg"}:
            path.read_bytes().decode("utf-8")  # raises, naming nothing, if not
