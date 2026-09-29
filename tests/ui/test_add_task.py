"""Queueing tasks from forms built from the API schema (milestone 10): the
built-in tasks, the tutorial's own, enums, instruments, checks and errors."""

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, Running

from pyacquisition import Task
from pyacquisition.instruments import Lakeshore_350, Mercury_IPS

SIMULATED_RIG = Path(__file__).parents[2] / "examples" / "simulated_rig"
sys.path.insert(0, str(SIMULATED_RIG))
from sweep_rig import MyExperiment as Tutorial  # noqa: E402


@dataclass
class Checked(Task):
    """Hold for a while.

    Attributes:
        dwell (int): How long to hold, in seconds.
    """

    dwell: int = 60

    def __post_init__(self):
        super().__post_init__()
        if self.dwell <= 0:
            raise ValueError("The dwell must be more than 0 seconds.")

    async def run(self, experiment):
        await self.sleep(self.dwell)


class Rig(Tutorial):
    """The tutorial's rig, with two of each instrument that has tasks of its own
    (so the forms ask which), and a second task manager."""

    def setup(self):
        super().setup()
        for uid in ("cryo_a", "cryo_b"):
            self.add_instrument(Lakeshore_350(uid, f"GPIB0::{len(uid)}::INSTR", adapter="mock"))
        for uid in ("magnet_a", "magnet_b"):
            self.add_instrument(Mercury_IPS(uid, "GPIB0::9::INSTR", adapter="mock"))
        self.register_task(Checked)
        self.add_task_manager("control")


@pytest.fixture
def rig(tmp_path):
    running = Running(Rig, tmp_path)
    # Held, so queued tasks wait where they can be looked at.
    running.get("/task_manager/pause")
    running.get("/managers/control/pause")
    yield running
    running.stop()


def queue_of(rig, manager="main"):
    return rig.get("/managers/state").json()["data"][manager]["queue"]


def open_dialog(context, rig, manager="Main"):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    page.page.get_by_role("tab", name="Queue").click()
    page.page.get_by_role("button", name=f"Add a task to {manager}").click()
    dialog = page.page.get_by_role("dialog", name=f"Add a task to {manager}")
    expect(dialog.get_by_role("option").first).to_be_visible()
    return page, dialog


def pick(dialog, name):
    dialog.get_by_role("option").filter(has_text=name).first.click()
    expect(dialog.locator(".task-form-title")).to_have_text(name)


def field(dialog, name):
    return dialog.locator(f".form-field[data-field='{name}']")


# -------------------------------------------------------------- the list
def test_every_task_is_offered_and_the_search_is_ready(context, rig):
    page, dialog = open_dialog(context, rig)

    names = dialog.locator(".task-option-name").all_inner_texts()
    for name in (
        "NewFile",
        "WaitFor",
        "WaitUntil",
        "Ramp Temperature",
        "Sweep Magnetic Field",
        "Set Temperature",
        "Record At",
        "Temperature Sweep",
        "Checked",
    ):
        assert name in names
    expect(dialog.get_by_role("searchbox", name="Search tasks")).to_be_focused()
    assert page.errors == []


def test_the_search_narrows_the_list(context, rig):
    page, dialog = open_dialog(context, rig)

    dialog.get_by_role("searchbox", name="Search tasks").fill("sweep")

    expect(dialog.locator(".task-option-name")).to_have_text(
        ["Sweep Magnetic Field", "Temperature Sweep"]
    )


def test_the_keyboard_moves_through_the_list_and_into_the_form(context, rig):
    page, dialog = open_dialog(context, rig)
    search = dialog.get_by_role("searchbox", name="Search tasks")
    search.fill("wait")
    expect(dialog.locator(".task-form-title")).to_have_text("WaitFor")

    search.press("ArrowDown")
    expect(dialog.locator(".task-form-title")).to_have_text("WaitUntil")
    search.press("Enter")

    expect(field(dialog, "hour").locator("input")).to_be_focused()


# -------------------------------------------------------------- queueing
def test_a_task_is_queued_with_the_values_given(context, rig):
    page, dialog = open_dialog(context, rig)
    pick(dialog, "WaitFor")
    # Each field starts at its default, and says what it is for.
    expect(field(dialog, "minutes").locator("input")).to_have_value("0")
    expect(field(dialog, "minutes")).to_contain_text("The number of minutes to wait.")

    field(dialog, "minutes").locator("input").fill("2")
    dialog.get_by_role("button", name="Add to queue").click()

    expect(dialog.get_by_role("status")).to_have_text("WaitFor added to the queue.")
    (task,) = queue_of(rig)
    assert task["name"] == "WaitFor"
    assert task["parameters"] == {"hours": 0, "minutes": 2, "seconds": 0}


def test_the_tutorials_tasks_are_queued_too(context, rig):
    page, dialog = open_dialog(context, rig)
    pick(dialog, "Temperature Sweep")

    field(dialog, "low").locator("input").fill("10")
    field(dialog, "high").locator("input").fill("50")
    field(dialog, "step").locator("input").fill("2.5")
    dialog.get_by_role("button", name="Add to queue").click()

    expect(dialog.get_by_role("status")).to_contain_text("added")
    (task,) = queue_of(rig)
    assert task["parameters"] == {"low": 10.0, "high": 50.0, "step": 2.5, "dwell": 60}


def test_several_can_be_queued_without_closing(context, rig):
    page, dialog = open_dialog(context, rig)
    pick(dialog, "WaitFor")

    for count, seconds in enumerate(("5", "10"), start=1):
        field(dialog, "seconds").locator("input").fill(seconds)
        dialog.get_by_role("button", name="Add to queue").click()
        # The queue in the tab behind shows each as it is added.
        expect(page.page.locator(".manager[data-manager='main'] .queued-task")).to_have_count(count)

    assert [t["parameters"]["seconds"] for t in queue_of(rig)] == [5, 10]


def test_a_checkbox_sends_true_or_false(context, rig):
    page, dialog = open_dialog(context, rig)
    pick(dialog, "NewFile")

    field(dialog, "file_name").locator("input").fill("cooldown")
    field(dialog, "increment_block").get_by_role("checkbox").check()
    dialog.get_by_role("button", name="Add to queue").click()

    expect(dialog.get_by_role("status")).to_contain_text("added")
    (task,) = queue_of(rig)
    assert task["parameters"]["increment_block"] is True
    assert task["parameters"]["file_name"] == "cooldown"


def test_enums_and_instruments_are_lists_to_choose_from(context, rig):
    page, dialog = open_dialog(context, rig)
    pick(dialog, "Ramp Temperature")
    lakeshore = field(dialog, "lakeshore").locator("select")
    channel = field(dialog, "output_channel").locator("select")

    expect(lakeshore.locator("option")).to_have_text(["Choose…", "cryo_a", "cryo_b"])
    expect(channel.locator("option")).to_contain_text(["Output 1", "Output 2"])

    lakeshore.select_option("cryo_b")
    channel.select_option(label="Output 2")
    field(dialog, "setpoint").locator("input").fill("4.2")
    field(dialog, "ramp_rate").locator("input").fill("1")
    dialog.get_by_role("button", name="Add to queue").click()

    expect(dialog.get_by_role("status")).to_contain_text("added")
    (task,) = queue_of(rig)
    assert task["parameters"]["lakeshore"] == "cryo_b"
    assert "OUTPUT_2" in str(task["parameters"]["output_channel"])


def test_a_task_goes_to_the_task_manager_it_was_added_to(context, rig):
    page, dialog = open_dialog(context, rig, manager="Control")
    pick(dialog, "WaitFor")

    dialog.get_by_role("button", name="Add to queue").click()

    expect(dialog.get_by_role("status")).to_contain_text("added")
    assert len(queue_of(rig, "control")) == 1
    assert queue_of(rig) == []


# -------------------------------------------------------------- mistakes
def test_a_missing_value_is_shown_by_its_field_and_nothing_is_sent(context, rig):
    page, dialog = open_dialog(context, rig)
    pick(dialog, "Temperature Sweep")

    field(dialog, "high").locator("input").fill("50")
    dialog.get_by_role("button", name="Add to queue").click()

    expect(field(dialog, "low").locator(".form-error")).to_have_text("Required.")
    expect(field(dialog, "low").locator("input")).to_have_attribute("aria-invalid", "true")
    expect(field(dialog, "high").locator(".form-error")).to_have_count(0)
    assert queue_of(rig) == []


def test_a_value_of_the_wrong_kind_is_explained(context, rig):
    page, dialog = open_dialog(context, rig)
    pick(dialog, "Record At")

    field(dialog, "kelvin").locator("input").fill("four")
    field(dialog, "dwell").locator("input").fill("1.5")
    dialog.get_by_role("button", name="Add to queue").click()

    expect(field(dialog, "kelvin").locator(".form-error")).to_have_text(
        "A number, such as 1.5 or 2e-3."
    )
    expect(field(dialog, "dwell").locator(".form-error")).to_have_text(
        "A whole number, such as 3."
    )
    assert queue_of(rig) == []

    # Typing again clears the complaint.
    field(dialog, "kelvin").locator("input").fill("4")
    expect(field(dialog, "kelvin").locator(".form-error")).to_have_count(0)


def test_what_the_task_says_is_wrong_is_shown(context, rig):
    page, dialog = open_dialog(context, rig)
    pick(dialog, "Checked")

    field(dialog, "dwell").locator("input").fill("0")
    dialog.get_by_role("button", name="Add to queue").click()

    expect(dialog.get_by_role("alert")).to_have_text("The dwell must be more than 0 seconds.")
    assert queue_of(rig) == []


# -------------------------------------------------------------- closing
@pytest.mark.parametrize("how", ["escape", "done"])
def test_the_dialog_closes(context, rig, how):
    page, dialog = open_dialog(context, rig)

    if how == "escape":
        page.page.keyboard.press("Escape")
    else:
        dialog.get_by_role("button", name="Done").click()

    expect(dialog).to_have_count(0)


def test_with_one_task_manager_it_is_just_add_a_task(context, tmp_path):
    from ui_helpers import SmokeExperiment

    running = Running(SmokeExperiment, tmp_path)
    try:
        page = Page(context.new_page())
        page.page.goto(f"{running.address}/")
        page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
        page.page.get_by_role("tab", name="Queue").click()
        page.page.get_by_role("button", name="Add a task").click()
        expect(page.page.get_by_role("dialog", name="Add a task")).to_be_visible()
    finally:
        running.stop()
