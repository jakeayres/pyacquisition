"""The Ctrl+K palette with arguments typed on its search line (the command
palette's milestone 1): `wait 0 5` and Enter queues a five-minute wait, and
what is wrong shows before anything is sent."""

import re

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import expect
from test_queue import QueueRig
from ui_helpers import Page, Running


@pytest.fixture(scope="module")
def rig(tmp_path_factory):
    running = Running(QueueRig, tmp_path_factory.mktemp("palette"), measurement_period=0.05)
    # Held, so queued tasks wait where they can be looked at.
    running.get("/task_manager/pause")
    running.get("/managers/control/pause")
    yield running
    running.stop()


@pytest.fixture
def page(context, rig):
    page = Page(context.new_page())
    page.page.goto(f"{rig.address}/")
    page.page.wait_for_function("window.pyacquisition?.store?.current?.rows > 5", timeout=15000)
    yield page
    rig.get("/task_manager/clear_tasks")
    rig.get("/managers/control/clear_tasks")
    assert page.errors == [], f"the page logged errors: {page.errors}"


def palette(page):
    return page.page.get_by_role("dialog", name="Command palette")


def open_palette(page):
    page.page.keyboard.press("Control+k")
    dialog = palette(page)
    expect(dialog.get_by_role("option").first).to_be_visible()
    return dialog


def type_line(page, text):
    """Opens the palette and types `text` on its search line: the dialog, and
    the search box."""
    dialog = open_palette(page)
    search = dialog.get_by_role("searchbox")
    search.press_sequentially(text)
    return dialog, search


def field(dialog, name):
    return dialog.locator(f".form-field[data-field='{name}']")


def queued(rig, manager="main"):
    return [
        (task["name"], task["parameters"])
        for task in rig.get("/managers/state").json()["data"][manager]["queue"]
    ]


def test_typed_arguments_fill_the_form_and_enter_queues_it(page, rig):
    dialog, search = type_line(page, "wait 0 5")

    expect(dialog.locator(".task-form-title")).to_have_text("WaitFor")
    expect(field(dialog, "hours").locator("input")).to_have_value("0")
    expect(field(dialog, "minutes").locator("input")).to_have_value("5")
    expect(dialog.locator(".palette-args")).to_contain_text("hours=0")
    expect(dialog.locator(".palette-args")).to_contain_text("✓ Enter to queue")

    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("WaitFor", {"hours": 0, "minutes": 5, "seconds": 0})]


def test_a_named_argument_and_a_positional_one(page, rig):
    _, search = type_line(page, "wait seconds=30 0")

    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("WaitFor", {"hours": 0, "minutes": 0, "seconds": 30})]


def test_words_after_the_search_are_text(page, rig):
    _, search = type_line(page, "new file cold")

    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("NewFile", {"file_name": "cold", "increment_block": False})]


def test_tab_locks_in_the_item_so_every_word_after_it_is_an_argument(page, rig):
    dialog, search = type_line(page, "newf")

    search.press("Tab")
    expect(search).to_have_value("NewFile ")
    expect(search).to_be_focused()
    search.press_sequentially("cold run")
    expect(field(dialog, "file_name").locator("input")).to_have_value("cold run")
    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("NewFile", {"file_name": "cold run", "increment_block": False})]


def test_quotes_hold_spaces(page, rig):
    _, search = type_line(page, 'new file "cold run"')

    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("NewFile", {"file_name": "cold run", "increment_block": False})]


@pytest.mark.parametrize(
    "text, where, problem",
    [
        ("wait abc", "hours", "Nothing left here takes abc"),
        ("wait 1 2 3 4", "seconds", "4 has nowhere to go"),
    ],
)
def test_a_problem_shows_before_enter_and_enter_goes_to_it(page, rig, text, where, problem):
    dialog, search = type_line(page, text)

    expect(dialog.locator(".palette-arg-problem")).to_contain_text(problem)
    expect(field(dialog, where).locator(".form-error")).to_contain_text(problem)
    expect(dialog.locator(".palette-arg-ready")).to_have_count(0)

    search.press("Enter")

    expect(field(dialog, where).locator("input")).to_be_focused()
    expect(dialog).to_be_visible()
    assert queued(rig) == []


def test_the_problem_goes_once_the_field_is_changed(page, rig):
    dialog, search = type_line(page, "wait abc")
    search.press("Enter")
    hours = field(dialog, "hours")

    hours.locator("input").fill("1")

    expect(hours.locator(".form-error")).to_have_count(0)
    hours.locator("input").press("Enter")
    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("WaitFor", {"hours": 1, "minutes": 0, "seconds": 0})]


def test_an_instrument_called_inline_answers_and_the_palette_stays_open(page):
    dialog, search = type_line(page, "clock start_timer lap")
    expect(dialog.locator(".task-form-title")).to_have_text("clock.start_timer")
    search.press("Enter")
    expect(dialog.locator(".palette-answer")).to_be_visible()

    search.fill("")
    search.press_sequentially("clock read_timer lap")
    expect(dialog.locator(".palette-args")).to_contain_text("✓ Enter to read")
    search.press("Enter")

    answer = dialog.locator(".palette-answer .result-value")
    expect(answer).to_have_text(re.compile(r"^\d+(\.\d+)?(e-?\d+)?$"))
    expect(dialog).to_be_visible()


def test_an_item_with_inputs_and_nothing_typed_after_it_goes_to_its_form(page, rig):
    dialog, search = type_line(page, "new file")
    expect(dialog.locator(".palette-args")).to_have_count(0)

    search.press("Enter")

    expect(field(dialog, "file_name").locator("input")).to_be_focused()
    assert queued(rig) == []


def test_an_item_without_inputs_runs_on_enter(page):
    dialog, search = type_line(page, "clock time")
    expect(dialog.locator(".task-form-title")).to_have_text("clock.time")

    search.press("Enter")

    expect(dialog.locator(".palette-answer .result-value")).to_have_text(re.compile(r"^\d"))


def test_an_item_whose_inputs_all_have_defaults_still_goes_to_its_form(page, rig):
    dialog, search = type_line(page, "explode control")

    search.press("Enter")

    expect(field(dialog, "message").locator("input")).to_be_focused()
    assert queued(rig, "control") == []


def test_the_arrow_keys_pick_another_match_for_the_arguments(page, rig):
    dialog, search = type_line(page, "wait 0 5")
    expect(dialog.locator(".task-form-title")).to_have_text("WaitFor")

    search.press("ArrowDown")

    expect(dialog.locator(".task-form-title")).to_have_text("WaitUntil")


# -------------------------------------------------------------- queueing a call
def test_shift_enter_queues_an_instrument_call(page, rig):
    dialog, search = type_line(page, "clock start_timer lap")
    expect(dialog.locator(".palette-arg-ready")).to_have_text("✓ Enter to send · Shift+Enter to queue")

    search.press("Shift+Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("clock.start_timer", {"name": "lap"})]


def test_add_to_queue_on_the_form_queues_it(page, rig):
    dialog, _ = type_line(page, "clock read_timer lap")

    dialog.get_by_role("button", name="Add to queue").click()

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("clock.read_timer", {"name": "lap"})]


def test_a_call_can_be_queued_on_another_task_manager(page, rig):
    dialog, _ = type_line(page, "clock time")
    expect(dialog.get_by_label("Queue on")).to_have_value("main")

    dialog.get_by_label("Queue on").select_option("control")
    dialog.get_by_role("button", name="Add to queue").click()

    expect(palette(page)).to_have_count(0)
    assert queued(rig, "control") == [("clock.time", None)]
    assert queued(rig) == []


def test_a_task_has_no_second_button(page):
    dialog, _ = type_line(page, "wait")

    expect(dialog.locator(".task-form-title")).to_have_text("WaitFor")
    expect(dialog.get_by_role("button", name="Add to queue")).to_have_count(1)  # its own
    expect(dialog.get_by_label("Queue on")).to_have_count(0)


def test_a_queued_query_runs_and_its_value_is_the_last_result(page, rig):
    for line in ("clock start_timer lap", "clock read_timer lap"):
        _, search = type_line(page, line)
        search.press("Shift+Enter")
        expect(palette(page)).to_have_count(0)
    assert [name for name, _ in queued(rig)] == ["clock.start_timer", "clock.read_timer"]

    rig.get("/task_manager/resume")
    try:
        page.page.get_by_role("tab", name="Queue").click()
        expect(page.page.locator(".queue-last").first).to_contain_text(
            re.compile(r"clock\.read_timer completed → \d")
        )
    finally:
        rig.get("/task_manager/pause")


def test_a_queue_holding_a_call_is_saved_and_loaded_again(page, rig):
    _, search = type_line(page, "clock start_timer lap")
    search.press("Shift+Enter")
    assert rig.get("/sequences/save", name="with a call", manager="main").status_code == 200
    rig.get("/task_manager/clear_tasks")
    assert queued(rig) == []

    assert rig.get("/sequences/load", name="with a call", manager="main").status_code == 200

    assert queued(rig) == [("clock.start_timer", {"name": "lap"})]
    rig.get("/sequences/delete", name="with a call")


# -------------------------------------------------------------- actions
def rack_state(rig):
    return rig.get("/rack/state").json()


def run_line(page, text, key="Enter"):
    dialog, search = type_line(page, text)
    expect(dialog.locator(".task-form-title")).to_be_visible()
    search.press(key)
    return dialog


def until(page, condition):
    """Waits for `condition`, JavaScript given the state of the experiment's
    task managers (`m`), its rack (`r`) and its scribe (`s`)."""
    page.page.wait_for_function(
        f"""Promise.all(['/managers/state', '/rack/state', '/scribe/state'].map(
            (p) => fetch(p).then((r) => r.json()))).then(([m, r, s]) => {condition})"""
    )


def test_new_data_file_runs_at_once_and_its_task_is_found_too(page, rig):
    dialog, search = type_line(page, "new file")
    rows = dialog.locator(".palette-option")
    expect(rows.filter(has_text="New data file").locator(".palette-tag")).to_have_text("Experiment")
    expect(rows.filter(has_text="NewFile").first.locator(".palette-tag")).to_have_text("Task · Main")
    search.fill("")

    search.press_sequentially("new data file cold")
    expect(dialog.locator(".palette-arg-ready")).to_have_text("✓ Enter to run · Shift+Enter to queue")
    search.press("Enter")

    expect(palette(page)).to_have_count(0)
    until(page, "s.data.file.endsWith('cold.data')")
    assert queued(rig) == []


def test_shift_enter_on_new_data_file_queues_newfile(page, rig):
    run_line(page, "new data file later", "Shift+Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("NewFile", {"file_name": "later", "increment_block": False})]


def test_pausing_and_resuming_the_measurements_runs_at_once(page, rig):
    try:
        run_line(page, "pause measurements")
        until(page, "r.paused")
        expect(page.page.get_by_role("button", name="Measurements", exact=True)).to_contain_text("Paused")

        dialog, search = type_line(page, "measurements")
        names = dialog.locator(".task-option-name")
        expect(names.filter(has_text=re.compile("^Resume measurements$"))).to_have_count(1)
        expect(names.filter(has_text=re.compile("^Pause measurements$"))).to_have_count(0)
        search.fill("resume measurements")
        search.press("Enter")
        until(page, "!r.paused")
    finally:
        rig.get("/rack/resume/")


def test_shift_enter_queues_the_pause_and_the_measurements_carry_on(page, rig):
    run_line(page, "pause measurements", "Shift+Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("PauseMeasurements", None)]
    assert rack_state(rig)["paused"] is False


def test_setting_the_period_now_or_in_its_turn(page, rig):
    try:
        run_line(page, "set measurement period 0.5")
        until(page, "r.period === 0.5")
        expect(page.page.get_by_role("button", name="Measurements", exact=True)).to_contain_text("Every 0.5 s")

        run_line(page, "set measurement period 2", "Shift+Enter")
        expect(palette(page)).to_have_count(0)
        assert queued(rig) == [("SetMeasurementPeriod", {"period": 2.0})]
        assert rack_state(rig)["period"] == 0.5
    finally:
        rig.get("/rack/period/set/", period=0.05)


def test_a_period_of_zero_is_refused_and_says_why(page, rig):
    dialog, search = type_line(page, "set measurement period 0")
    search.press("Enter")

    expect(dialog.locator(".form-error").first).to_be_visible()
    assert rack_state(rig)["period"] == 0.05
    page.errors = [e for e in page.errors if "422" not in e]


def test_the_theme_switches_and_its_label_follows(page):
    before = page.page.evaluate("document.documentElement.dataset.theme")
    after = "dark" if before == "light" else "light"

    run_line(page, f"switch to the {after} theme")

    expect(page.page.locator("html")).to_have_attribute("data-theme", after)
    dialog, search = type_line(page, "theme")
    expect(dialog.locator(".task-option-name").first).to_have_text(f"Switch to the {before} theme")
    search.press("Enter")  # and back
    expect(page.page.locator("html")).to_have_attribute("data-theme", before)


def test_a_tab_opens_and_the_dock_hides(page):
    logs = page.page.get_by_role("tab", name="Logs")

    run_line(page, "open the logs tab")
    expect(logs).to_have_attribute("aria-selected", "true")

    run_line(page, "hide or show the dock")
    expect(page.page.get_by_role("tabpanel")).to_have_count(0)
    run_line(page, "hide or show the dock")
    expect(page.page.get_by_role("tabpanel")).to_have_count(1)


def test_a_queue_is_resumed_and_paused_by_its_name(page, rig):
    try:
        dialog, search = type_line(page, "queue control")
        expect(dialog.locator(".task-option-name").first).to_have_text("Resume queue (Control)")
        search.press("Enter")
        until(page, "m.data.control.status !== 'Paused'")

        run_line(page, "pause queue control")
        until(page, "m.data.control.status === 'Paused'")
    finally:
        rig.get("/managers/control/pause")


def test_clearing_a_queue_asks_first_and_cancelling_does_nothing(page, rig):
    rig.get("/tasks/waitfor", hours=0, minutes=0, seconds=5)

    run_line(page, "clear queue main")

    question = page.page.get_by_role("alertdialog", name="Clear the Main queue?")
    expect(question).to_be_visible()
    expect(palette(page)).to_have_count(0)
    question.get_by_role("button", name="Cancel").click()
    expect(question).to_have_count(0)
    assert len(queued(rig)) == 1

    run_line(page, "clear queue main")
    page.page.get_by_role("alertdialog").get_by_role("button", name="Clear queue").click()
    until(page, "m.data.main.queue.length === 0")


def test_aborting_asks_first(page, rig):
    rig.get("/tasks/waitfor", hours=0, minutes=0, seconds=30)
    rig.get("/task_manager/resume")
    try:
        until(page, "!!m.data.main.current_task")
        dialog, search = type_line(page, "abort running task main")
        expect(dialog.locator(".task-form-title")).to_have_text("Abort running task (Main)")
        search.press("Enter")

        question = page.page.get_by_role("alertdialog", name="Abort WaitFor?")
        expect(question).to_be_visible()
        question.get_by_role("button", name="Cancel").click()
        expect(question).to_have_count(0)
        assert rig.get("/managers/state").json()["data"]["main"]["current_task"]["name"] == "WaitFor"
    finally:
        rig.get("/task_manager/abort")
        rig.get("/task_manager/pause")


def test_shutting_down_asks_first(page, rig):
    run_line(page, "shut down")

    close = page.page.get_by_role("alertdialog")
    expect(close).to_contain_text("This stops the experiment")
    page.page.keyboard.press("Escape")
    expect(close).to_have_count(0)
    assert rig.get("/ping").status_code == 200


def test_a_saved_sequence_is_loaded(page, rig):
    rig.get("/tasks/waitfor", hours=0, minutes=1, seconds=0)
    rig.get("/sequences/save", name="one wait", manager="main")
    rig.get("/task_manager/clear_tasks")
    try:
        run_line(page, "load saved sequence 'one wait'")

        expect(palette(page)).to_have_count(0)
        assert queued(rig) == [("WaitFor", {"hours": 0, "minutes": 1, "seconds": 0})]
    finally:
        rig.get("/sequences/delete", name="one wait")


def test_the_data_folder_is_only_offered_in_the_apps_window(page):
    dialog, _ = type_line(page, "open the data folder")

    expect(dialog.locator(".task-option-name", has_text="Open the data folder")).to_have_count(0)


def test_going_to_the_last_error_is_offered_once_there_is_one(page, rig):
    dialog, _ = type_line(page, "go to the last error")
    expect(dialog.locator(".task-option-name", has_text="Go to the last error")).to_have_count(0)
    page.page.keyboard.press("Escape")

    rig.get("/managers/control/tasks/explode", message="kaboom")
    rig.get("/managers/control/resume")
    try:
        page.page.wait_for_function(
            "window.pyacquisition.logs.entries.some("
            "(e) => (e.level === 'error' || e.level === 'exception') && e.message.includes('kaboom'))",
            timeout=10000,
        )
        run_line(page, "go to the last error")

        expect(page.page.get_by_role("tab", name="Logs")).to_have_attribute("aria-selected", "true")
        # The newest error: the task manager's, just after the task's own.
        expect(page.page.get_by_role("region", name="Log message")).to_contain_text("Explode failed")
        expect(page.page.locator(".log-row.selected")).to_be_in_viewport()
    finally:
        rig.get("/managers/control/pause")
        page.errors = [e for e in page.errors if "kaboom" not in e]


def test_an_action_registered_by_a_later_feature_is_found_and_runs(page):
    page.page.evaluate(
        """import('/ui/js/actions.js').then((a) => a.registerAction({
            name: "say-hello",
            label: "Say hello",
            tag: "Test",
            description: "Proves an action can be added.",
            run: () => { window.hello = "hello"; },
        }))"""
    )

    run_line(page, "say hello")

    expect(palette(page)).to_have_count(0)
    assert page.page.evaluate("window.hello") == "hello"


# -------------------------------------------------------------- recents
def options(dialog):
    return dialog.locator(".palette-list > li")


def recent_rows(dialog):
    return dialog.locator(".palette-recent")


def seed_recents(page, recents):
    """Recents as an earlier session left them, before the palette opens."""
    page.page.evaluate(
        "(list) => sessionStorage.setItem('pyacquisition:recents', JSON.stringify(list))", recents
    )


def test_an_empty_palette_offers_the_last_run_first_and_enter_repeats_it(page, rig):
    _, search = type_line(page, "wait 0 5")
    search.press("Enter")
    expect(palette(page)).to_have_count(0)

    dialog = open_palette(page)

    expect(options(dialog).first).to_have_text("Recent")
    first = recent_rows(dialog).first
    expect(first).to_have_attribute("aria-selected", "true")
    expect(first).to_contain_text("WaitFor")
    expect(first).to_contain_text("hours=0, minutes=5, seconds=0")
    expect(dialog.locator(".palette-heading")).to_have_text(["Recent", "Everything"])
    expect(field(dialog, "minutes").locator("input")).to_have_value("5")
    expect(dialog.locator(".palette-args")).to_contain_text("Enter to queue again")

    dialog.get_by_role("searchbox").press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("WaitFor", {"hours": 0, "minutes": 5, "seconds": 0})] * 2


def test_tab_opens_a_recents_form_and_a_change_is_a_new_recent_above_it(page, rig):
    _, search = type_line(page, "wait 0 5")
    search.press("Enter")
    expect(palette(page)).to_have_count(0)
    dialog = open_palette(page)

    dialog.get_by_role("searchbox").press("Tab")

    hours = field(dialog, "hours").locator("input")
    expect(hours).to_be_focused()
    expect(hours).to_have_value("0")
    minutes = field(dialog, "minutes").locator("input")
    expect(minutes).to_have_value("5")
    minutes.fill("7")
    minutes.press("Enter")
    expect(palette(page)).to_have_count(0)

    dialog = open_palette(page)
    expect(recent_rows(dialog)).to_have_count(2)
    expect(recent_rows(dialog).nth(0)).to_contain_text("minutes=7")
    expect(recent_rows(dialog).nth(1)).to_contain_text("minutes=5")


def test_the_same_run_twice_is_one_recent_and_twenty_are_kept(page, rig):
    for _ in range(2):
        _, search = type_line(page, "wait 0 5")
        search.press("Enter")
        expect(palette(page)).to_have_count(0)
    dialog = open_palette(page)
    expect(recent_rows(dialog)).to_have_count(1)
    page.page.keyboard.press("Escape")

    kept = page.page.evaluate(
        """import('/ui/js/recents.js').then((r) => {
            for (let i = 0; i < 21; i++) r.recordRun({ id: '/tasks/waitfor', label: 'WaitFor' }, { n: String(i) });
            return r.recents().map((x) => x.values.n);
        })"""
    )
    assert len(kept) == 20
    assert kept[0] == "20" and kept[-1] == "1"  # newest first, the oldest dropped


def test_a_recent_queued_is_queued_again_and_says_so(page, rig):
    _, search = type_line(page, "clock start_timer lap")
    search.press("Shift+Enter")
    expect(palette(page)).to_have_count(0)

    dialog = open_palette(page)
    first = recent_rows(dialog).first
    expect(first).to_contain_text("clock.start_timer")
    expect(first.locator(".palette-tag")).to_have_text("Queued")
    expect(dialog.locator(".palette-args")).to_contain_text("Enter to queue it again")
    dialog.get_by_role("searchbox").press("Enter")

    expect(palette(page)).to_have_count(0)
    assert queued(rig) == [("clock.start_timer", {"name": "lap"})] * 2


def test_a_failed_run_is_not_kept(page, rig):
    dialog, search = type_line(page, "clock read_timer never")
    search.press("Enter")
    expect(dialog.locator(".form-error, .form-problem").first).to_be_visible()
    page.errors = [e for e in page.errors if "500" not in e]
    page.page.keyboard.press("Escape")

    dialog = open_palette(page)

    expect(dialog.locator(".palette-heading")).to_have_count(0)


def test_typing_hides_the_recents(page, rig):
    _, search = type_line(page, "wait 0 5")
    search.press("Enter")
    expect(palette(page)).to_have_count(0)
    dialog = open_palette(page)
    expect(recent_rows(dialog)).to_have_count(1)

    dialog.get_by_role("searchbox").press_sequentially("clock")

    expect(recent_rows(dialog)).to_have_count(0)
    expect(dialog.locator(".palette-heading")).to_have_count(0)


def test_a_recent_whose_item_is_gone_is_hidden(page, rig):
    seed_recents(page, [{"id": "/tasks/retired", "label": "Retired", "values": {}, "at": 1}])

    dialog = open_palette(page)

    expect(dialog.locator(".palette-heading")).to_have_count(0)
    # Hidden, not deleted: it comes back if the task does.
    kept = page.page.evaluate("import('/ui/js/recents.js').then((r) => r.recents().length)")
    assert kept == 1


def test_a_recent_whose_inputs_no_longer_pass_goes_to_its_form(page, rig):
    seed_recents(page, [{
        "id": "/tasks/waitfor", "label": "WaitFor", "at": 1,
        "values": {"hours": "soon", "minutes": "5", "seconds": "0"},
    }])
    dialog = open_palette(page)
    expect(dialog.locator(".palette-arg-problem")).to_contain_text("no longer pass")

    dialog.get_by_role("searchbox").press("Enter")

    hours = field(dialog, "hours")
    expect(hours.locator("input")).to_be_focused()
    expect(hours.locator(".form-error")).to_be_visible()
    assert queued(rig) == []
