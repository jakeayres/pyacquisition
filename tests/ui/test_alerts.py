"""Alerts: a toast and the bell's count for an error logged, a task failing, data
stopping, and the connection dropping; one alert for each (milestone 17)."""

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from test_queue import QueueRig, queue
from ui_helpers import Page, Running

from pyacquisition.core.logging import logger


class AlertRig(QueueRig):
    def setup(self):
        super().setup()

        @self._api_server.app.get("/test/log")
        async def log(message: str, level: str = "error", count: int = 1):
            for n in range(count):
                getattr(logger, level)(message.format(n=n))
            return {"status": 200}

        # Rows stop reaching the page (and the history), while the measurements
        # carry on: data has stopped arriving.
        @self._api_server.app.get("/test/stall")
        async def stall():
            self._calculations.unsubscribe(self._history)
            return {"status": 200}

        @self._api_server.app.get("/test/unstall")
        async def unstall():
            self._history.subscribe_to(self._calculations)
            return {"status": 200}


@pytest.fixture
def rig(tmp_path):
    running = Running(AlertRig, tmp_path, measurement_period=0.05)
    yield running
    running.stop()


def open_page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.logs?.status === 'live'")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    page.page.get_by_role("status").filter(has_text="Connected").wait_for()
    return page


def toasts(page):
    return page.page.get_by_role("region", name="Alerts").get_by_role("alert")


def bell(page):
    return page.page.locator(".alert-bell .icon-button")


# -------------------------------------------------------------- errors
def test_an_error_logged_raises_one_alert(context, rig):
    page = open_page(context, rig)

    rig.get("/test/log", message="[Lakeshore] no answer on GPIB0::12")

    expect(toasts(page)).to_have_count(1)
    expect(toasts(page).first).to_contain_text("An error was logged")
    expect(toasts(page).first).to_contain_text("[Lakeshore] no answer on GPIB0::12")
    expect(bell(page)).to_have_attribute("aria-label", "Alerts, 1 new")
    assert page.errors == []


def test_a_burst_of_errors_is_one_alert(context, rig):
    page = open_page(context, rig)

    rig.get("/test/log", message="failure {n}", count=5)

    expect(toasts(page)).to_have_count(1)
    expect(toasts(page).first.locator(".alert-count")).to_have_text("×5")


def test_errors_from_before_the_page_opened_raise_nothing(context, rig):
    rig.get("/test/log", message="an old error", count=3)

    page = open_page(context, rig)
    page.page.wait_for_timeout(1500)

    expect(toasts(page)).to_have_count(0)
    expect(bell(page)).to_have_attribute("aria-label", "Alerts")


def test_warnings_raise_nothing(context, rig):
    page = open_page(context, rig)

    rig.get("/test/log", message="just so you know", level="warning")
    page.page.wait_for_timeout(1500)

    expect(toasts(page)).to_have_count(0)


# -------------------------------------------------------------- a task failing
def test_a_task_failing_is_one_alert_that_says_so(context, rig):
    page = open_page(context, rig)

    # A failing task also logs errors: they are the same alert.
    queue(rig, task="explode", message="the magnet quenched")

    toast = toasts(page).first
    expect(toast).to_contain_text("Explode failed", timeout=8000)
    expect(toast).to_contain_text("RuntimeError: the magnet quenched. The queue is paused")
    expect(toast).to_contain_text("The queue is paused")
    expect(toasts(page)).to_have_count(1)
    page.page.wait_for_timeout(1500)
    expect(toasts(page)).to_have_count(1)
    expect(bell(page)).to_have_attribute("aria-label", "Alerts, 1 new")


def test_each_failure_is_an_alert_of_its_own(context, rig):
    page = open_page(context, rig)
    queue(rig, task="explode", message="first")
    expect(toasts(page).first).to_contain_text("Explode failed", timeout=8000)

    page.page.wait_for_timeout(5500)  # past the time alerts are merged in
    rig.get("/task_manager/resume")
    queue(rig, task="explode", message="second")

    expect(bell(page)).to_have_attribute("aria-label", "Alerts, 2 new", timeout=8000)


# -------------------------------------------------------------- data stopping
def test_data_stopping_raises_one_alert_for_each_stall(context, rig):
    page = open_page(context, rig)

    rig.get("/test/stall")
    expect(toasts(page).first).to_contain_text("No data is arriving", timeout=10000)
    page.page.wait_for_timeout(3000)  # longer still: still the one alert
    expect(bell(page)).to_have_attribute("aria-label", "Alerts, 1 new")

    rig.get("/test/unstall")
    page.page.wait_for_function("window.pyacquisition.store.current.rows > 0")
    page.page.wait_for_timeout(1000)
    rig.get("/test/stall")

    expect(bell(page)).to_have_attribute("aria-label", "Alerts, 2 new", timeout=10000)


def test_paused_measurements_are_not_a_stall(context, rig):
    page = open_page(context, rig)
    page.page.wait_for_function("window.pyacquisition.store.current.rows > 5")

    rig.get("/rack/pause/")
    page.page.wait_for_timeout(7500)

    expect(bell(page)).to_have_attribute("aria-label", "Alerts")


# -------------------------------------------------------------- the connection
def test_the_connection_dropping_raises_an_alert(context, tmp_path):
    rig = Running(AlertRig, tmp_path)
    page = open_page(context, rig)

    rig.stop()

    expect(toasts(page).first).to_contain_text("The experiment stopped answering", timeout=15000)
    expect(toasts(page)).to_have_count(1)


def test_stopping_the_experiment_from_the_page_raises_no_alert(context, tmp_path):
    rig = Running(AlertRig, tmp_path)
    try:
        page = open_page(context, rig)

        page.page.get_by_role("button", name="Stop the experiment").click()
        page.page.get_by_role("button", name="Stop experiment").click()
        expect(page.page.get_by_role("status").filter(has_text="Disconnected")).to_be_visible(
            timeout=15000
        )
        page.page.wait_for_timeout(1000)

        expect(toasts(page)).to_have_count(0)
    finally:
        rig.stop()


# -------------------------------------------------------------- the bell
def test_alerts_can_be_dismissed_and_are_listed_under_the_bell(context, rig):
    page = open_page(context, rig)
    rig.get("/test/log", message="one")
    expect(toasts(page)).to_have_count(1)

    toasts(page).first.get_by_role("button", name="Dismiss").click()
    expect(toasts(page)).to_have_count(0)

    bell(page).click()
    listing = page.page.get_by_role("dialog", name="Recent alerts")
    expect(listing.locator(".alert-item")).to_have_count(1)
    expect(listing).to_contain_text("one")
    expect(bell(page)).to_have_attribute("aria-label", "Alerts")  # read now

    listing.get_by_role("button", name="Clear").click()
    expect(listing).to_contain_text("No alerts.")


def test_a_toast_goes_by_itself(context, rig):
    page = open_page(context, rig)
    rig.get("/test/log", message="brief")
    expect(toasts(page)).to_have_count(1)

    expect(toasts(page)).to_have_count(0, timeout=13000)
    expect(bell(page)).to_have_attribute("aria-label", "Alerts, 1 new")  # still to see
