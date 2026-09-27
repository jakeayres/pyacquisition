"""Run on the setup page: it saves what isn't saved, then starts the experiment
from the file, and the page goes to the experiment's (milestone 8 of
specs/setup-page.md). The whole of `open_setup` runs in a thread, with no
window, so the handover is the real one."""

import threading
import time

import pytest
import requests

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, free_port

from pyacquisition.core.setup import open_setup


def rig(tmp_path) -> str:
    return (
        f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n\n'
        "[instruments]\n"
        'clock = {instrument = "Clock"}\n\n'
        "[measurements]\n"
        't = {instrument = "clock", method = "timestamp_ms"}\n'
    )


class Setup:
    """`pyacquisition new` with no window, in a thread."""

    def __init__(self, path):
        self.port = free_port()
        self.address = f"http://localhost:{self.port}"
        self.thread = threading.Thread(
            target=open_setup, args=(path, self.port, False), daemon=True
        )
        self.thread.start()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                requests.get(f"{self.address}/ping", timeout=1)
                return
            except requests.exceptions.RequestException:
                time.sleep(0.1)
        pytest.fail("the setup server never answered")

    def stop(self):
        """Stops the experiment, or the setup server, whichever is running."""
        for path in ("/experiment/shutdown", "/setup/shutdown"):
            try:
                requests.get(f"{self.address}{path}", timeout=5)
            except requests.exceptions.RequestException:
                pass
        self.thread.join(timeout=30)


@pytest.fixture
def rig_file(tmp_path):
    path = tmp_path / "rig.toml"
    path.write_text(rig(tmp_path), encoding="utf-8")
    return path


@pytest.fixture
def setup(rig_file):
    running = Setup(rig_file)
    yield running
    running.stop()


def open_setup_page(context, running):
    page = Page(context.new_page())
    page.page.goto(f"{running.address}/")
    page.page.get_by_role("heading", name="Instruments").wait_for()
    expect(page.page.get_by_label("TOML")).not_to_be_empty()
    return page


def run_button(page):
    return page.page.get_by_role("button", name="Run")


def test_run_starts_the_experiment_and_the_page_goes_to_it(context, setup):
    page = open_setup_page(context, setup)

    run_button(page).click()

    page.page.wait_for_url(f"{setup.address}/ui/", timeout=30000)
    expect(page.page.get_by_role("status").filter(has_text="Connected")).to_be_visible(
        timeout=15000
    )
    assert requests.get(f"{setup.address}/experiment/info", timeout=5).json()["data"] == {
        "name": "rig"
    }


def test_run_saves_what_is_not_saved_first(context, setup, rig_file):
    page = open_setup_page(context, setup)
    page.page.get_by_role("navigation", name="Sections").get_by_role(
        "button", name="Options"
    ).click()
    page.page.locator("#option-rack-period").fill("0.5")
    expect(run_button(page)).to_have_attribute(
        "title", "Save the file, and start the experiment from it"
    )

    run_button(page).click()

    page.page.wait_for_url(f"{setup.address}/ui/", timeout=30000)
    assert "[rack]\nperiod = 0.5\n" in rig_file.read_text(encoding="utf-8")
    rack = requests.get(f"{setup.address}/rack/state", timeout=5).json()
    assert rack["period"] == 0.5


def test_run_waits_until_there_are_no_problems(context, setup, rig_file):
    page = open_setup_page(context, setup)
    expect(run_button(page)).to_be_enabled()
    page.page.get_by_role("navigation", name="Sections").get_by_role(
        "button", name="Options"
    ).click()

    page.page.locator("#option-rack-period").fill("fast")

    expect(run_button(page)).to_be_disabled()
    assert "fast" not in rig_file.read_text(encoding="utf-8")
