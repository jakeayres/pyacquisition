"""The Instruments tab: every instrument's queries and commands, called from
forms, with their recent results (milestone 14). On the tutorial's simulated
cryostat and lock-in."""

import json
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from ui_helpers import Page, Running

SIMULATED_RIG = Path(__file__).parents[2] / "examples" / "simulated_rig"
sys.path.insert(0, str(SIMULATED_RIG))
from sweep_rig import MyExperiment as Tutorial  # noqa: E402

NUMBER = re.compile(r"^-?\d+(\.\d+)?(e[-+]?\d+)?$")


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    running = Running(Tutorial, tmp_path_factory.mktemp("instruments"))
    yield running
    running.stop()


def open_tab(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.status === 'live'")
    page.page.get_by_role("tab", name="Instruments").click()
    expect(page.page.get_by_role("list", name="Instruments")).to_be_visible()
    return page


def instrument(page, uid):
    page.page.get_by_role("list", name="Instruments").get_by_role("button", name=re.compile(f"^{uid}")).click()


def method(page, name):
    page.page.locator(".method-item", has_text=re.compile(f"^{name}$")).click()
    expect(page.page.locator(".call-title")).to_have_text(re.compile(f"\\.{name}$"))


def results(page):
    return page.page.locator(".result")


# -------------------------------------------------------------- what is shown
def test_every_instrument_is_listed_with_what_it_is(context, rig):
    page = open_tab(context, rig)

    items = page.page.get_by_role("list", name="Instruments").get_by_role("button")
    expect(items).to_have_count(3)
    expect(items.nth(1)).to_contain_text("lakeshore")
    expect(items.nth(1)).to_contain_text("Simulated Cryostat")
    assert page.errors == []


def test_an_instruments_queries_and_commands_are_listed_apart(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lakeshore")

    queries = page.page.get_by_role("list", name="Queries").locator(".method-item")
    commands = page.page.get_by_role("list", name="Commands").locator(".method-item")
    expect(queries).to_have_text(["get_ramp", "get_setpoint", "get_temperature"])
    expect(commands).to_have_text(["set_ramp", "set_setpoint"])


def test_the_search_narrows_the_list(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lakeshore")

    page.page.get_by_role("searchbox", name="Search the queries and commands").fill("setpoint")

    expect(page.page.locator(".method-item")).to_have_text(["get_setpoint", "set_setpoint"])


# -------------------------------------------------------------- calling
def test_a_query_is_read_and_its_result_shown(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lakeshore")
    method(page, "get_temperature")

    page.page.locator(".form-field[data-field='input_channel'] select").select_option("Input A")
    page.page.get_by_role("button", name="Read").click()

    first = results(page).first
    expect(first.locator(".result-call")).to_contain_text("get_temperature(input_channel=Input A)")
    expect(first.locator(".result-value")).to_have_text(NUMBER)


def test_a_query_with_no_inputs_is_one_press(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lockin")
    method(page, "get_x")

    expect(page.page.locator(".endpoint-form")).to_contain_text("This takes no inputs.")
    page.page.get_by_role("button", name="Read").click()

    expect(results(page).first.locator(".result-value")).to_have_text(NUMBER)


def test_a_command_is_sent_and_its_effect_can_be_read_back(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lockin")
    method(page, "set_frequency")
    expect(page.page.locator(".call-kind")).to_have_text("Command")

    page.page.locator(".form-field[data-field='frequency'] input").fill("137.5")
    page.page.get_by_role("button", name="Send").click()
    sent = results(page).first
    expect(sent.locator(".result-call")).to_contain_text("set_frequency(frequency=137.5)")
    expect(sent).not_to_have_class(re.compile("failed"))

    method(page, "get_frequency")
    page.page.get_by_role("button", name="Read").click()

    expect(results(page).first.locator(".result-value")).to_have_text("137.5")
    assert rig.get("/lockin/get_frequency").json()["data"] == 137.5


def test_a_list_is_shown_as_rows_and_a_call_says_how_long_it_took(context, rig):
    page = open_tab(context, rig)
    instrument(page, "clock")
    method(page, "start_timer")
    page.page.locator(".form-field[data-field='name'] input").fill("cooldown")
    page.page.get_by_role("button", name="Send").click()
    expect(results(page)).to_have_count(1)

    method(page, "list_timers")
    page.page.get_by_role("button", name="Read", exact=True).click()
    expect(results(page)).to_have_count(2)

    first = results(page).first
    expect(first.locator(".result-row dt")).to_contain_text(["[0]"])
    expect(first.locator(".result-row dd")).to_contain_text(["cooldown"])
    expect(first.locator(".result-time")).to_have_text(re.compile(r"^\d+ ms · "))


def test_copy_takes_the_whole_result(context, rig):
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    page = open_tab(context, rig)
    instrument(page, "clock")
    method(page, "start_timer")
    page.page.locator(".form-field[data-field='name'] input").fill("warmup")
    page.page.get_by_role("button", name="Send").click()
    expect(results(page)).to_have_count(1)
    method(page, "list_timers")
    page.page.get_by_role("button", name="Read", exact=True).click()
    expect(results(page)).to_have_count(2)

    results(page).first.get_by_role("button", name="Copy the result").click()

    expect(results(page).first.get_by_role("status")).to_have_text("Copied")
    copied = page.page.evaluate("navigator.clipboard.readText()")
    assert "warmup" in json.loads(copied)


def test_a_bad_value_is_explained_and_not_sent(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lockin")
    method(page, "set_frequency")
    before = results(page).count()

    page.page.locator(".form-field[data-field='frequency'] input").fill("fast")
    page.page.get_by_role("button", name="Send").click()

    expect(page.page.locator(".form-field[data-field='frequency'] .form-error")).to_have_text(
        "A number, such as 1.5 or 2e-3."
    )
    assert results(page).count() == before


# -------------------------------------------------------------- results
def test_results_stay_per_instrument_while_the_page_is_open(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lockin")
    method(page, "get_y")
    page.page.get_by_role("button", name="Read").click()
    expect(results(page)).not_to_have_count(0)
    lockin_results = results(page).count()

    instrument(page, "clock")
    expect(page.page.locator(".instrument-results-empty")).to_be_visible()

    # Away to another tab and back: the lock-in's results are still there.
    page.page.get_by_role("tab", name="Values").click()
    page.page.get_by_role("tab", name="Instruments").click()
    instrument(page, "lockin")
    expect(results(page)).to_have_count(lockin_results)


def test_results_can_be_cleared(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lockin")
    method(page, "get_x")
    page.page.get_by_role("button", name="Read").click()
    expect(results(page)).not_to_have_count(0)

    page.page.locator(".instrument-results").get_by_role("button", name="Clear").click()

    expect(results(page)).to_have_count(0)
    expect(page.page.locator(".instrument-results-empty")).to_be_visible()


def test_the_choice_lasts_for_the_session(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lakeshore")
    method(page, "set_ramp")

    page.page.reload()
    page.page.get_by_role("tab", name="Instruments").click()

    expect(page.page.locator(".call-title")).to_have_text("lakeshore.set_ramp")


def test_an_enum_input_is_titled_after_the_input(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lakeshore")
    method(page, "set_setpoint")

    expect(page.page.locator(".form-field[data-field='output_channel'] label")).to_have_text(
        re.compile(r"^Output Channel")
    )


# -------------------------------------------------------------- queueing a call
def test_a_call_is_queued_from_its_form_and_its_value_shown_in_the_queue(context, rig):
    rig.get("/task_manager/pause")
    try:
        page = open_tab(context, rig)
        instrument(page, "lakeshore")
        method(page, "get_temperature")
        page.page.locator(".call-pane select").first.select_option(label="Input A")

        page.page.get_by_role("button", name="Add to queue").click()

        page.page.wait_for_function(
            "fetch('/managers/state').then(r => r.json()).then(s => s.data.main.queue.length === 1)"
        )
        (task,) = rig.get("/managers/state").json()["data"]["main"]["queue"]
        assert task["name"] == "lakeshore.get_temperature"
        assert task["parameters"] == {"input_channel": "INPUT_A"}

        # Run, it reads the temperature, and the Queue tab says what it read.
        rig.get("/task_manager/resume")
        page.page.get_by_role("tab", name="Queue").click()
        expect(page.page.locator(".queue-last").first).to_contain_text(
            re.compile(r"lakeshore\.get_temperature completed → \d+\.\d+")
        )
        assert page.errors == []
    finally:
        rig.get("/task_manager/clear_tasks")
        rig.get("/task_manager/resume")


def test_a_call_that_isnt_a_query_or_command_has_no_add_to_queue(context, rig):
    page = open_tab(context, rig)
    instrument(page, "lakeshore")
    method(page, "get_temperature")

    expect(page.page.get_by_role("button", name="Add to queue")).to_be_visible()
    # One task manager: no list of them.
    expect(page.page.get_by_label("Queue on")).to_have_count(0)


def test_the_docs_example_queues_a_setpoint_from_the_palette(context, rig):
    rig.get("/task_manager/pause")
    try:
        page = open_tab(context, rig)
        page.page.keyboard.press("Control+k")
        search = page.page.get_by_role("searchbox", name="Search tasks, instruments and actions")
        search.press_sequentially("lakeshore set_setpoint output_1 300")
        expect(page.page.locator(".palette-arg-ready")).to_be_visible()

        search.press("Shift+Enter")

        page.page.wait_for_function(
            "fetch('/managers/state').then(r => r.json()).then(s => s.data.main.queue.length === 1)"
        )
        (task,) = rig.get("/managers/state").json()["data"]["main"]["queue"]
        assert task["description"] == "lakeshore.set_setpoint(output_channel=OUTPUT_1, setpoint=300.0)"
    finally:
        rig.get("/task_manager/clear_tasks")
        rig.get("/task_manager/resume")
