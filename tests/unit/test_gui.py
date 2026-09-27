"""The GUI: choosing it, serving its page, and its window and the experiment
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
from pyacquisition.gui.window import Lifeline


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


# -------------------------------------------------------------- choosing the GUI
# False makes the window too, but doesn't start it.
@pytest.mark.parametrize("value", [True, "new", "NEW", False])
def test_the_gui_option_says_whether_the_window_runs(tmp_path, value):
    experiment = Experiment(root_path=str(tmp_path), gui=value)

    assert isinstance(experiment._gui, Gui)
    assert experiment._run_gui is (value is not False)


@pytest.mark.parametrize("value", ["yes", "modern", 1, 0.5])
def test_an_unknown_gui_is_refused(tmp_path, value):
    class MyExperiment(Experiment):
        root_path = str(tmp_path)
        gui = value

    with pytest.raises(ValueError, match="`gui` must be True, False or 'new'"):
        MyExperiment()


@pytest.mark.parametrize("value", ["classic", "Classic"])
def test_the_classic_gui_is_refused_and_why(tmp_path, value):
    with pytest.raises(ValueError, match="The classic GUI .* has been removed"):
        Experiment(root_path=str(tmp_path), gui=value)


def test_the_gui_can_be_chosen_in_toml(tmp_path):
    config = tmp_path / "rig.toml"
    config.write_text(
        f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n\n[gui]\nrun = "new"\n'
    )

    experiment = Experiment.from_config(str(config))

    assert isinstance(experiment._gui, Gui)


def test_the_gui_uses_the_api_server_address(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui="new", api_server_port=8123)

    assert experiment._gui.server == "http://localhost:8123"


def test_a_server_on_every_interface_is_reached_through_localhost():
    assert Gui(host="0.0.0.0", port=9000).server == "http://localhost:9000"


def test_the_gui_can_be_sent_to_its_process():
    gui = pickle.loads(pickle.dumps(Gui(port=8123)))

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
    gui = Gui(port=8123)
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

    gui = Gui(port=8123)
    flag = gui.run_in_new_process()._args[1]
    window = Process(target=watch_then_leave, args=(flag,))
    window.start()
    window.join(timeout=10)

    closing = threading.Thread(target=gui.close, daemon=True)
    closing.start()
    closing.join(timeout=2)

    assert not closing.is_alive()


def test_telling_a_gui_that_never_started_to_close_does_nothing():
    Gui().close()


class FakeWebviewWindow:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


def test_the_window_closes_at_once_when_told(monkeypatch):
    from types import SimpleNamespace

    from pyacquisition.gui import window

    pings = []
    monkeypatch.setattr(window, "ping", lambda server: pings.append(1) or True)
    app = window._Window("http://localhost:1")
    app.window = FakeWebviewWindow()

    app.watch(SimpleNamespace(value=True))

    assert app.window.destroyed
    assert len(pings) <= 1  # it did not wait for the experiment to stop answering


def test_the_window_closes_when_the_experiment_stops_answering(monkeypatch):
    from pyacquisition.gui import window

    answers = iter([True, False, False, False])
    monkeypatch.setattr(window, "ping", lambda server: next(answers))
    monkeypatch.setattr(window, "PING_PERIOD", 0.01)
    app = window._Window("http://localhost:1")
    app.window = FakeWebviewWindow()

    app.watch()

    assert app.window.destroyed


# -------------------------------------------------------------- handing the window over
def test_a_restarted_lifeline_waits_again_as_at_the_start():
    clock = Clock()
    lifeline = Lifeline(missed=3, startup_timeout=60, clock=clock)
    lifeline.record(True)

    clock.now = 100
    lifeline.restart()

    clock.now = 159
    assert not any(lifeline.record(False) for _ in range(10))
    clock.now = 161
    assert lifeline.record(False)


def test_the_window_can_be_handed_over():
    gui = Gui(port=8123, page="/ui/setup/")
    process = gui.run_in_new_process()
    _, _, address, handing_over = process._args

    assert address.value == b"http://localhost:8123"
    assert process._kwargs == {"page": "/ui/setup/"}
    assert not handing_over.value

    gui.start_handover()
    assert handing_over.value

    gui.host, gui.port = "0.0.0.0", 8124
    gui.end_handover()
    assert address.value == b"http://localhost:8124"
    assert not handing_over.value


def test_handing_over_a_window_that_never_started_does_nothing():
    gui = Gui()

    gui.start_handover()
    gui.end_handover()


class SharedAddress:
    """As the shared address: bytes in `value`."""

    def __init__(self, address):
        self.value = address.encode()


class LoadingWindow(FakeWebviewWindow):
    def __init__(self):
        super().__init__()
        self.loaded = []

    def load_url(self, url):
        self.loaded.append(url)


def watch_in_thread(app, *flags):
    import threading

    thread = threading.Thread(target=app.watch, args=flags, daemon=True)
    thread.start()
    return thread


def wait_until(check, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.01)
    return False


def test_failed_pings_are_ignored_while_handing_over(monkeypatch):
    from types import SimpleNamespace

    from pyacquisition.gui import window

    pings = []
    monkeypatch.setattr(window, "ping", lambda server: pings.append(server) or False)
    monkeypatch.setattr(window, "PING_PERIOD", 0.01)
    app = window._Window("http://localhost:1")
    app.window = FakeWebviewWindow()

    thread = watch_in_thread(app, None, SimpleNamespace(value=True))
    time.sleep(0.2)  # many more periods than MISSED_PINGS

    assert not app.window.destroyed
    assert pings == []  # nothing to check while its server goes away on purpose
    app.close()
    thread.join(timeout=2)


def test_the_window_closes_if_its_parent_goes_while_handing_over(monkeypatch):
    from types import SimpleNamespace

    from pyacquisition.gui import window

    monkeypatch.setattr(window, "PING_PERIOD", 0.01)
    monkeypatch.setattr(window, "parent_alive", lambda: False)
    app = window._Window("http://localhost:1")
    app.window = FakeWebviewWindow()

    app.watch(None, SimpleNamespace(value=True))

    assert app.window.destroyed


def test_the_window_follows_the_shared_address(monkeypatch):
    from types import SimpleNamespace

    from pyacquisition.gui import window

    up = {"http://localhost:8123"}
    pinged = []

    def ping(server):
        pinged.append(server)
        return server in up

    monkeypatch.setattr(window, "ping", ping)
    monkeypatch.setattr(window, "PING_PERIOD", 0.01)
    address = SharedAddress("http://localhost:8123")
    handing_over = SimpleNamespace(value=False)
    app = window._Window("http://localhost:8123", address)
    app.window = LoadingWindow()
    thread = watch_in_thread(app, None, handing_over)
    assert wait_until(lambda: pinged)

    # Handed over to a server on another port, which takes a while to answer.
    handing_over.value = True
    up.clear()
    address.value = b"http://localhost:8124"
    handing_over.value = False
    assert wait_until(lambda: pinged[-1] == "http://localhost:8124")
    time.sleep(0.1)  # more than MISSED_PINGS: it waits, as for a new server
    assert not app.window.destroyed
    assert app.window.loaded == []

    up.add("http://localhost:8124")
    assert wait_until(lambda: app.window.loaded)
    assert app.window.loaded == ["http://localhost:8124/"]  # its own page
    assert app.server == "http://localhost:8124"  # for the data folder, and closing
    app.close()
    thread.join(timeout=2)


def test_a_window_on_the_same_address_is_left_to_its_page(monkeypatch):
    from types import SimpleNamespace

    from pyacquisition.gui import window

    answers = iter([True, False, False, True, True, True])
    monkeypatch.setattr(window, "ping", lambda server: next(answers, True))
    monkeypatch.setattr(window, "PING_PERIOD", 0.01)
    handing_over = SimpleNamespace(value=False)
    app = window._Window("http://localhost:8123", SharedAddress("http://localhost:8123"))
    app.window = LoadingWindow()
    thread = watch_in_thread(app, None, handing_over)

    time.sleep(0.2)

    assert app.window.loaded == []
    assert not app.window.destroyed
    app.close()
    thread.join(timeout=2)


class HandoverGui:
    """A stand-in for a `Gui` whose window is already open, being handed over."""

    def __init__(self):
        self.host = self.port = None
        self.handed_to = None

    def run_in_new_process(self):
        raise AssertionError("an adopted window is not started again")

    def end_handover(self):
        self.handed_to = (self.host, self.port)

    def close(self):
        pass  # its process ends by itself


def test_an_adopted_window_is_watched_and_not_started_again(tmp_path):
    port = free_port()
    experiment = Experiment(root_path=str(tmp_path), gui=False, api_server_port=port)
    gui = HandoverGui()
    window = Process(target=time.sleep, args=(0.5,))
    window.start()

    experiment._adopt_gui(gui, window)
    asyncio.run(asyncio.wait_for(experiment._run(), timeout=20))

    assert gui.handed_to == ("localhost", port)
    assert experiment._ui_process is window
    assert experiment._shutdown_event.is_set()  # it stopped when the window went
    assert experiment._started


def test_an_adopted_window_is_left_open_if_the_experiment_fails_to_start(tmp_path):
    class Broken(Experiment):
        def setup(self):
            raise RuntimeError("the magnet is not answering")

    experiment = Broken(root_path=str(tmp_path), gui=False, api_server_port=free_port())
    gui = HandoverGui()
    gui.close = lambda: pytest.fail("the window was told to close")
    window = FakeProcess(alive=True)

    experiment._adopt_gui(gui, window)
    asyncio.run(asyncio.wait_for(experiment._run(), timeout=20))

    assert gui.handed_to is None  # still being handed over, for the setup page
    assert not experiment._started
    assert "the magnet is not answering" in str(experiment._error)


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

    def close(self):
        pass  # its process ends by itself


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

    from pyacquisition.gui import window

    asked = []

    def urlopen(url, timeout):
        asked.append(url)
        return io.BytesIO(json.dumps({"status": 200, "data": str(tmp_path)}).encode())

    monkeypatch.setattr(window.urllib.request, "urlopen", urlopen)

    assert window.data_folder("http://localhost:8123") == str(tmp_path)
    assert asked == ["http://localhost:8123/scribe/current_directory"]


def test_there_is_no_data_folder_while_the_experiment_does_not_answer():
    from pyacquisition.gui import window

    with socket.socket() as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    assert window.data_folder(f"http://localhost:{port}") is None


def test_a_folder_is_opened_only_if_it_exists(monkeypatch, tmp_path):
    from pyacquisition.gui import window

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

    import pyacquisition.gui

    static = Path(pyacquisition.gui.__file__).parent / "static"
    for path in static.rglob("*"):
        if path.suffix in {".js", ".css", ".html", ".svg"}:
            path.read_bytes().decode("utf-8")  # raises, naming nothing, if not


# -------------------------------------------------------------- saving an export
class FakeDialogWindow:
    """A window whose Save dialog answers as told, and notes how it was asked."""

    def __init__(self, answer):
        self.answer = answer
        self.asked = None

    def create_file_dialog(self, kind, directory="", save_filename="", file_types=()):
        self.asked = {"directory": directory, "name": save_filename, "types": file_types}
        return self.answer


def api_with(monkeypatch, tmp_path, answer):
    from types import SimpleNamespace

    from pyacquisition.gui import window

    monkeypatch.setattr(window, "data_folder", lambda server: str(tmp_path))
    owner = SimpleNamespace(server="http://localhost:1", window=FakeDialogWindow(answer))
    return window._Api(owner), owner.window


def test_an_export_is_saved_where_the_dialog_says(monkeypatch, tmp_path):
    target = tmp_path / "chosen.csv"
    api, dialog = api_with(monkeypatch, tmp_path, [str(target)])

    where = api.save_file("plot.csv", text="time,T\r\n1,4.2\r\n")

    assert where == str(target)
    assert target.read_bytes() == b"time,T\r\n1,4.2\r\n"  # as it is: no line endings changed
    assert dialog.asked == {
        "directory": str(tmp_path),  # the data folder
        "name": "plot.csv",
        "types": ("CSV file (*.csv)",),
    }


def test_an_image_is_saved_from_its_base64(monkeypatch, tmp_path):
    import base64

    target = tmp_path / "plot.png"
    api, _ = api_with(monkeypatch, tmp_path, str(target))  # some versions give a string
    png = b"\x89PNG\r\n\x1a\n...image..."

    api.save_file("plot.png", base64=base64.b64encode(png).decode())

    assert target.read_bytes() == png


def test_a_cancelled_dialog_saves_nothing(monkeypatch, tmp_path):
    api, _ = api_with(monkeypatch, tmp_path, None)

    assert api.save_file("plot.csv", text="x") is None
    assert list(tmp_path.iterdir()) == []


def test_the_save_dialog_is_shown_on_the_windows_own_thread(monkeypatch):
    """pywebview on Windows shows the dialog on the calling thread, and the
    page's calls come on a thread of their own, which can't show it."""
    import sys
    import threading
    from types import ModuleType, SimpleNamespace

    from pyacquisition.gui import window

    shown_on = []

    class View:
        InvokeRequired = True

        def Invoke(self, func):  # as Windows Forms does: on the window's thread
            done = threading.Thread(target=func, name="window thread")
            done.start()
            done.join()

    class Func:
        def __class_getitem__(cls, _):
            return lambda fn: fn

    fake = ModuleType("webview.platforms.winforms")
    fake.BrowserView = SimpleNamespace(instances={"master": View()})
    fake.Func = Func
    fake.Type = object
    monkeypatch.setitem(sys.modules, "webview.platforms.winforms", fake)

    class Window:
        uid = "master"

        def create_file_dialog(self, kind, **options):
            shown_on.append(threading.current_thread().name)
            return ("C:/chosen.csv",)

    assert window.ask_where_to_save(Window(), save_filename="a.csv") == ("C:/chosen.csv",)
    assert shown_on == ["window thread"]


def test_without_windows_forms_the_dialog_is_shown_directly(monkeypatch):
    import sys

    from pyacquisition.gui import window

    monkeypatch.delitem(sys.modules, "webview.platforms.winforms", raising=False)
    dialog = FakeDialogWindow("/tmp/chosen.csv")

    assert window.ask_where_to_save(dialog, save_filename="a.csv") == "/tmp/chosen.csv"


# -------------------------------------------------------------- without WebView2
def fake_winforms(monkeypatch, renderer):
    import sys
    from types import ModuleType

    fake = ModuleType("webview.platforms.winforms")
    fake.renderer = renderer
    monkeypatch.setitem(sys.modules, "webview.platforms.winforms", fake)
    monkeypatch.delenv("PYWEBVIEW_GUI", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")


def test_internet_explorers_engine_is_noticed(monkeypatch):
    from pyacquisition.gui import window

    fake_winforms(monkeypatch, "mshtml")
    assert window.needs_webview2() is True

    fake_winforms(monkeypatch, "edgechromium")
    assert window.needs_webview2() is False


def test_an_engine_chosen_for_pywebview_is_followed(monkeypatch):
    from pyacquisition.gui import window

    fake_winforms(monkeypatch, "edgechromium")
    monkeypatch.setenv("PYWEBVIEW_GUI", "mshtml")
    assert window.needs_webview2() is True
    monkeypatch.setenv("PYWEBVIEW_GUI", "cef")
    assert window.needs_webview2() is False


def test_webview2_is_windows_only(monkeypatch):
    import sys

    from pyacquisition.gui import window

    monkeypatch.setattr(sys, "platform", "linux")
    assert window.needs_webview2() is False


def run_main(monkeypatch, needs):
    """Runs the window process's `main` with a fake pywebview, and returns what
    the window was made with."""
    import sys
    from types import ModuleType, SimpleNamespace

    from pyacquisition.gui import window

    made = {}
    fake = ModuleType("webview")

    class Events:  # `window.events.closing += handler`
        def __init__(self):
            self.closing = self

        def __iadd__(self, handler):
            return self

    def create_window(title, **options):
        made.update(options, title=title)
        return SimpleNamespace(events=Events())

    fake.create_window = create_window
    fake.start = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "webview", fake)
    monkeypatch.setattr(window.signal, "signal", lambda *args: None)
    monkeypatch.setattr(window, "needs_webview2", lambda: needs)
    window.main("http://localhost:8123")
    return made


def test_the_window_shows_the_page(monkeypatch):
    made = run_main(monkeypatch, needs=False)

    assert made["url"] == "http://localhost:8123/ui/"
    assert "html" not in made


def test_without_webview2_the_window_says_what_to_do(monkeypatch):
    from pyacquisition.gui import window

    made = run_main(monkeypatch, needs=True)

    assert "url" not in made
    assert "WebView2 Runtime" in made["html"]
    assert window.WEBVIEW2_DOWNLOAD in made["html"]
    assert "http://localhost:8123" in made["html"]  # to open in a browser meanwhile
