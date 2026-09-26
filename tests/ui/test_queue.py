"""The Queue tab: every task manager, its running task and its queue, with
pause, resume, abort, remove, move and clear (milestone 9)."""

import asyncio
import time
from dataclasses import dataclass

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, Running, SmokeExperiment

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.instruments import Clock


@dataclass
class Explode(Task):
    """Fails at once."""

    message: str = "boom"

    async def run(self, experiment):
        raise RuntimeError(self.message)


@dataclass
class SlowStop(Task):
    """Runs until aborted, then takes a while to tidy up."""

    seconds: float = 2.0

    async def run(self, experiment):
        await self.wait_until(lambda: False)

    async def teardown(self, experiment):
        await asyncio.sleep(self.seconds)


class QueueRig(Experiment):
    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)
        self.add_measurement(Measurement("time", clock.time))
        self.add_task_manager("control")
        self.register_task(Explode)
        self.register_task(SlowStop)


@pytest.fixture
def rig(tmp_path):
    running = Running(QueueRig, tmp_path)
    yield running
    running.stop()


def queue(rig, task="waitfor", manager="main", **params):
    prefix = "" if manager == "main" else f"/managers/{manager}"
    if task == "waitfor":  # it asks for all three
        params = {"hours": 0, "minutes": 0, "seconds": 0, **params}
    assert rig.get(f"{prefix}/tasks/{task}", **params).status_code == 200


def state(rig, manager="main"):
    return rig.get("/managers/state").json()["data"][manager]


def wait_for(condition, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return
        time.sleep(0.05)
    raise AssertionError("the condition never held")


def open_queue(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    page.page.get_by_role("tab", name="Queue").click()
    return page


def panel(page, name):
    return page.page.get_by_role("region", name=name, exact=True)


def badge(section):
    """A task manager's state, as its header shows it."""
    return section.locator(".manager-head").get_by_role("status")


def queued_names(section):
    return section.locator(".queued-task .task-name").all_inner_texts()


# -------------------------------------------------------------- what is shown
def test_every_task_manager_is_shown(context, rig):
    page = open_queue(context, rig)

    for name in ("Main", "Control"):
        expect(panel(page, name)).to_be_visible()
        expect(badge(panel(page, name))).to_have_text("Idle")
        expect(panel(page, name)).to_contain_text("Nothing is running")
    assert page.errors == []


def test_one_task_manager_is_just_the_task_queue(context, tmp_path):
    running = Running(SmokeExperiment, tmp_path)
    try:
        running.get("/tasks/waitfor", hours=0, minutes=0, seconds=30)
        page = open_queue(context, running)
        expect(panel(page, "Task queue")).to_be_visible()

        panel(page, "Task queue").get_by_role("button", name="Abort").click()
        expect(page.page.get_by_role("alertdialog")).to_contain_text(
            "runs its teardown. The queue is then paused"
        )
    finally:
        running.stop()


def test_the_running_task_and_the_queue_are_shown(context, rig):
    queue(rig, seconds=30)
    queue(rig, minutes=2)
    queue(rig, task="explode", message="later")
    page = open_queue(context, rig)
    main = panel(page, "Main")

    running = main.get_by_label("Running task")
    expect(running).to_contain_text("WaitFor")
    expect(running.locator(".task-parameter").filter(has_text="seconds")).to_contain_text("30")
    expect(badge(main)).to_have_text("Running")
    expect(main.locator(".queued-task")).to_have_count(2)
    assert queued_names(main) == ["WaitFor", "Explode"]
    expect(main.locator(".queue-count")).to_have_text("2 queued")


def test_tasks_queued_elsewhere_show(context, rig):
    page = open_queue(context, rig)
    control = panel(page, "Control")

    queue(rig, manager="control", seconds=30)

    expect(control.get_by_label("Running task")).to_contain_text("WaitFor")


# -------------------------------------------------------------- pause and resume
def test_a_task_manager_can_be_paused_and_resumed(context, rig):
    queue(rig, seconds=30)
    page = open_queue(context, rig)
    main = panel(page, "Main")

    main.get_by_role("button", name="Pause").click()

    expect(badge(main)).to_have_text("Paused")
    assert state(rig)["status"] == "Paused"
    assert state(rig, "control")["status"] == "Running"  # each on its own

    main.get_by_role("button", name="Resume").click()

    expect(badge(main)).to_have_text("Running")
    assert state(rig)["status"] == "Running"


# -------------------------------------------------------------- abort
def test_abort_asks_first(context, rig):
    queue(rig, seconds=30)
    page = open_queue(context, rig)
    main = panel(page, "Main")

    main.get_by_role("button", name="Abort").click()
    dialog = page.page.get_by_role("alertdialog")
    expect(dialog).to_contain_text("Abort WaitFor?")
    expect(dialog).to_contain_text("The Main queue is then paused")
    dialog.get_by_role("button", name="Cancel").click()

    expect(dialog).to_have_count(0)
    assert state(rig)["current_task"]["name"] == "WaitFor"


def test_aborting_stops_the_task_and_says_the_queue_is_paused(context, rig):
    queue(rig, seconds=30)
    queue(rig, seconds=5)
    page = open_queue(context, rig)
    main = panel(page, "Main")

    main.get_by_role("button", name="Abort").click()
    page.page.get_by_role("alertdialog").get_by_role("button", name="Abort").click()

    expect(badge(main)).to_have_text("Paused")
    expect(main).to_contain_text("WaitFor was aborted, so this queue is paused")
    expect(main.locator(".queued-task")).to_have_count(1)  # the next one waits
    assert state(rig)["last_result"]["outcome"] == "aborted"


def test_a_task_that_is_stopping_shows_aborting(context, rig):
    queue(rig, task="slowstop", seconds=2)
    wait_for(lambda: state(rig)["current_task"] is not None)
    page = open_queue(context, rig)
    main = panel(page, "Main")

    rig.get("/task_manager/abort")

    expect(badge(main)).to_have_text("Aborting…")
    expect(main.get_by_role("button", name="Abort")).to_be_disabled()
    expect(badge(main)).to_have_text("Paused", timeout=10000)


# -------------------------------------------------------------- a failure
def test_a_failure_is_explained_and_can_be_resumed_from(context, rig):
    page = open_queue(context, rig)
    main = panel(page, "Main")
    queue(rig, task="explode", message="the magnet quenched")

    notice = main.get_by_role("alert")
    expect(notice).to_contain_text("Explode failed")
    expect(notice).to_contain_text("RuntimeError: the magnet quenched")
    expect(badge(main)).to_have_text("Paused")

    main.get_by_role("button", name="Resume").click()

    expect(notice).to_have_count(0)
    expect(main.locator(".queue-last")).to_contain_text("Explode failed")


# -------------------------------------------------------------- the queue
def test_a_queued_task_can_be_removed(context, rig):
    queue(rig, seconds=30)
    queue(rig, seconds=11)
    queue(rig, seconds=22)
    page = open_queue(context, rig)
    main = panel(page, "Main")
    expect(main.locator(".queued-task")).to_have_count(2)

    main.locator(".queued-task").first.get_by_role("button", name="Remove WaitFor").click()

    expect(main.locator(".queued-task")).to_have_count(1)
    (left,) = state(rig)["queue"]
    assert left["parameters"]["seconds"] == 22


def test_queued_tasks_can_be_moved(context, rig):
    queue(rig, seconds=30)
    queue(rig, seconds=11)
    queue(rig, task="explode", message="second")
    queue(rig, minutes=3)
    page = open_queue(context, rig)
    main = panel(page, "Main")
    rows = main.locator(".queued-task")
    expect(rows).to_have_count(3)

    # The ends can't go further.
    expect(rows.first.get_by_role("button", name="Move WaitFor up")).to_be_disabled()
    expect(rows.last.get_by_role("button", name="Move WaitFor down")).to_be_disabled()

    rows.nth(1).get_by_role("button", name="Move Explode up").click()

    expect(rows.first.locator(".task-name")).to_have_text("Explode")
    assert [t["name"] for t in state(rig)["queue"]] == ["Explode", "WaitFor", "WaitFor"]

    rows.first.get_by_role("button", name="Move Explode down").click()

    expect(rows.nth(1).locator(".task-name")).to_have_text("Explode")
    assert [t["name"] for t in state(rig)["queue"]] == ["WaitFor", "Explode", "WaitFor"]


def test_the_queue_can_be_cleared_after_asking(context, rig):
    queue(rig, seconds=30)
    queue(rig, seconds=11)
    queue(rig, seconds=22)
    page = open_queue(context, rig)
    main = panel(page, "Main")
    expect(main.locator(".queued-task")).to_have_count(2)

    main.get_by_role("button", name="Clear queue").click()
    dialog = page.page.get_by_role("alertdialog")
    expect(dialog).to_contain_text("This removes the 2 tasks waiting")
    dialog.get_by_role("button", name="Clear queue").click()

    expect(main.locator(".queued-task")).to_have_count(0)
    expect(main.locator(".queue-count")).to_have_text("Nothing queued")
    assert state(rig)["queue"] == []
    assert state(rig)["current_task"]["name"] == "WaitFor"  # carries on


def test_escape_cancels_a_question(context, rig):
    queue(rig, seconds=30)
    page = open_queue(context, rig)

    panel(page, "Main").get_by_role("button", name="Abort").click()
    page.page.keyboard.press("Escape")

    expect(page.page.get_by_role("alertdialog")).to_have_count(0)
    assert state(rig)["current_task"] is not None
