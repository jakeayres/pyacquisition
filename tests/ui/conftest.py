"""The new GUI's page, loaded in a real browser against a running experiment.

The browser is the installed Microsoft Edge, driven by Playwright, so no browser
needs downloading. Without Edge, these tests are skipped.
"""

import asyncio
import socket
import threading
import time

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


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    """The address of a running experiment, with no GUI of its own."""
    running = Running(SmokeExperiment, tmp_path_factory.mktemp("ui"))
    yield running.address
    running.stop()


# Module scope, not session: while Playwright runs, its event loop is the running
# loop on the main thread, and any asyncio test after it would fail with "cannot
# be called from a running event loop". It has to stop before other tests run.
@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import Error, sync_playwright

    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(channel="msedge")
    except Error:
        playwright.stop()
        pytest.skip("Microsoft Edge is not installed")
    yield browser
    browser.close()
    playwright.stop()


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


@pytest.fixture
def context(browser):
    """A fresh browser context, so no session state carries between tests.

    Reduced motion turns the page's transitions off (see app.css), so sizes can be
    measured straight after they change.
    """
    context = browser.new_context(viewport=VIEWPORT, reduced_motion="reduce")
    yield context
    context.close()


@pytest.fixture
def page(context, server):
    """The page, loaded and connected."""
    page = Page(context.new_page())
    page.page.goto(f"{server}/")
    page.page.get_by_role("status").filter(has_text="Connected").wait_for()
    yield page
    assert page.errors == [], f"the page logged errors: {page.errors}"
