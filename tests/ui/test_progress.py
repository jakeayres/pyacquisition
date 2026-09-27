"""How far along the running task is, on its card and in the top bar
(milestone 12)."""

import re
from dataclasses import dataclass

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from test_queue import QueueRig, queue
from ui_helpers import Page, Running

from pyacquisition import Task


@dataclass
class Held(Task):
    """Says how far along it is, and then waits.

    Attributes:
        fraction (float): How far along, from 0 to 1, when it counts no steps.
        step (int): The step it is on, when it counts steps.
        steps (int): How many steps there are, or 0 for none.
        note (str): What it says it is doing.
    """

    fraction: float = 0.25
    step: int = 0
    steps: int = 0
    note: str = ""

    async def run(self, experiment):
        if self.steps:
            self.set_progress(self.step, of=self.steps, note=self.note or None)
        else:
            self.set_progress(self.fraction, note=self.note or None)
        await self.wait_until(lambda: False, poll=0.2)


@dataclass
class Parent(Task):
    """Is on the second of three parts, which it runs as a subtask."""

    async def run(self, experiment):
        self.set_progress(1, of=3, note="the middle part")
        await self.run_subtask(Held(fraction=0.5, note="half way"))


class ProgressRig(QueueRig):
    def setup(self):
        super().setup()
        self.register_task(Held)
        self.register_task(Parent)


@pytest.fixture
def rig(tmp_path):
    running = Running(ProgressRig, tmp_path)
    yield running
    running.stop()


def open_page(context, rig, tab="Queue"):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    page.page.get_by_role("tab", name=tab).click()
    return page


def card(page, manager="Main"):
    return page.page.get_by_role("region", name=manager, exact=True).get_by_label("Running task")


# -------------------------------------------------------------- on the card
def test_a_wait_shows_how_far_along_it_is_and_the_time_left(context, rig):
    queue(rig, seconds=120)
    page = open_page(context, rig)
    running = card(page)

    bar = running.get_by_role("progressbar", name="WaitFor progress")
    expect(bar).to_be_visible()
    assert 0 <= int(bar.get_attribute("aria-valuenow")) <= 10
    expect(running.locator(".progress-left")).to_have_text(re.compile(r"^1:5\d left$|^2:00 left$"))
    expect(running.locator(".progress-elapsed")).to_have_text(re.compile(r"^Running for \d+ s$"))
    assert page.errors == []


def test_the_time_left_counts_down(context, rig):
    queue(rig, seconds=120)
    page = open_page(context, rig)
    left = card(page).locator(".progress-left")
    expect(left).to_be_visible()
    first = left.inner_text()

    expect(left).not_to_have_text(first, timeout=4000)


def test_steps_and_what_it_is_doing_are_shown(context, rig):
    queue(rig, task="held", step=2, steps=5, note="Point 3 at 4.2 K")
    page = open_page(context, rig)
    running = card(page)

    expect(running.locator(".progress-amount")).to_have_text("2 of 5")
    expect(running.locator(".progress-note")).to_have_text("Point 3 at 4.2 K")
    expect(running.get_by_role("progressbar")).to_have_attribute("aria-valuenow", "40")


def test_a_task_that_gives_no_time_left_gets_an_estimate(context, rig):
    queue(rig, task="held", fraction=0.5)
    page = open_page(context, rig)

    # Half way after about a second: about a second to go.
    expect(card(page).locator(".progress-left")).to_have_text(re.compile(r"^About \d+ s left$"))


def test_a_subtask_shows_its_own_progress_under_the_task(context, rig):
    queue(rig, task="parent")
    page = open_page(context, rig)
    running = card(page)

    expect(running.locator(".task-progress-line .progress-amount")).to_have_text("1 of 3")
    subtask = running.locator(".subtask-progress")
    expect(subtask.locator(".subtask-name")).to_have_text("Held")
    expect(subtask.locator(".progress-amount")).to_have_text("50%")
    expect(subtask.locator(".progress-note")).to_have_text("half way")


def test_a_task_that_says_nothing_shows_just_how_long_it_has_run(context, rig):
    queue(rig, task="slowstop")
    page = open_page(context, rig)
    running = card(page)

    expect(running.locator(".progress-elapsed")).to_have_text(re.compile(r"^Running for \d+ s$"))
    expect(running.get_by_role("progressbar")).to_have_count(0)


def test_the_time_run_stops_while_paused(context, rig):
    queue(rig, seconds=300)
    page = open_page(context, rig)
    elapsed = card(page).locator(".progress-elapsed")
    expect(elapsed).to_have_text(re.compile(r"Running for [1-9]\d* s"))

    rig.get("/task_manager/pause")
    page.page.wait_for_timeout(1500)  # for the pause to show
    held = elapsed.inner_text()
    page.page.wait_for_timeout(2500)

    assert elapsed.inner_text() == held


# -------------------------------------------------------------- the top bar
def test_the_top_bar_shows_the_running_task_and_opens_the_queue(context, rig):
    page = open_page(context, rig, tab="Values")
    summary = page.page.locator(".running-summary")
    expect(summary).to_have_count(0)  # nothing running

    queue(rig, seconds=120)

    expect(summary).to_contain_text("WaitFor")
    expect(summary.locator(".progress-left")).to_contain_text("left")
    summary.click()
    expect(page.page.get_by_role("tab", name="Queue")).to_have_attribute("aria-selected", "true")


def test_the_top_bar_counts_the_other_tasks_running(context, rig):
    queue(rig, seconds=120)
    queue(rig, manager="control", seconds=120)
    page = open_page(context, rig, tab="Values")

    summary = page.page.locator(".running-summary")
    expect(summary.locator(".running-more")).to_have_text("+1")
    expect(summary).to_have_attribute("aria-label", re.compile(r"and 1 more$"))
