"""What the browser tests share: a running experiment, a page that records its
errors, and small helpers. (Imported by name, not from conftest: another
conftest.py, such as tests/unit's, can be the module called `conftest` when
both folders are collected together.)
"""

import asyncio
import functools
import http.server
import shutil
import socket
import threading
import time
from pathlib import Path

import pytest
import requests

from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock

VIEWPORT = {"width": 1280, "height": 800}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


class SmokeExperiment(Experiment):
    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)
        self.add_measurement(Measurement("time", clock.time))


class Running:
    """An experiment running in a background thread, with no GUI of its own."""

    def __init__(self, experiment_class, root, port=None, **options):
        self.port = port or free_port()
        self.address = f"http://localhost:{self.port}"
        experiment = experiment_class(
            root_path=str(root), gui=False, api_server_port=self.port, **options
        )
        self.thread = threading.Thread(
            target=lambda: asyncio.run(experiment._run()), daemon=True
        )
        self.thread.start()
        for _ in range(100):
            try:
                requests.get(f"{self.address}/ping", timeout=1)
                return
            except requests.exceptions.RequestException:
                time.sleep(0.1)
        pytest.fail("the experiment never answered")

    def get(self, path, **params):
        return requests.get(f"{self.address}{path}", params=params, timeout=10)

    def stop(self):
        try:
            self.get("/experiment/shutdown")
        except requests.exceptions.RequestException:
            pass
        self.thread.join(timeout=15)


class SetupRunning:
    """A setup server (`pyacquisition new`) for a config file, running in a
    background thread, with no window."""

    def __init__(self, path, port=None):
        from pyacquisition.core.setup import SetupServer

        self.server = SetupServer(path, port=port or free_port())
        self.port = self.server.bind()
        self.address = f"http://localhost:{self.port}"
        self.thread = threading.Thread(
            target=lambda: asyncio.run(self.server.serve()), daemon=True
        )
        self.thread.start()
        for _ in range(100):
            try:
                requests.get(f"{self.address}/ping", timeout=1)
                return
            except requests.exceptions.RequestException:
                time.sleep(0.1)
        pytest.fail("the setup server never answered")

    def stop(self):
        if self.thread.is_alive():
            try:
                requests.get(f"{self.address}/setup/shutdown", timeout=5)
            except requests.exceptions.RequestException:
                pass
        self.thread.join(timeout=15)


class StaticSite:
    """A folder of files served over HTTP, in a background thread: the docs' demo,
    or a built docs site."""

    def __init__(self, folder):
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        class Server(http.server.ThreadingHTTPServer):
            # The interface asks for its forty-odd modules at once. With the
            # default backlog of 5, Windows refuses the rest of them.
            request_queue_size = 128

        handler = functools.partial(Quiet, directory=str(folder))
        self.server = Server(("127.0.0.1", 0), handler)
        self.address = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


REPO = Path(__file__).resolve().parents[2]


def copy_interface(destination):
    """Copies the interface's files to `destination`, as the docs build does for
    the front page's demo (.readthedocs.yml)."""
    shutil.copytree(
        REPO / "src" / "pyacquisition" / "gui" / "static", destination, dirs_exist_ok=True
    )


class Page:
    """A page, with the errors it logged to its console."""

    def __init__(self, page):
        self.page = page
        self.errors = []
        page.on(
            "console",
            lambda message: (
                message.type == "error" and self.errors.append(message.text)
            ),
        )
        # With the stack, so a failure says where in the page's code it came from.
        page.on(
            "pageerror",
            lambda error: self.errors.append(f"{error}\n{getattr(error, 'stack', '')}"),
        )


def set_log(page, axis, on=True, within=None):
    """Makes an axis logarithmic (or not) in a plot's axis settings. `within` is
    the panel, where there are several."""
    (within or page).get_by_role("button", name="Axis settings").click()
    menu = page.get_by_role("dialog", name="Axis settings")
    box = menu.get_by_label(f"Log {axis}")
    box.check() if on else box.uncheck()
    menu.get_by_role("button", name="Apply").click()
