"""The interface for several task managers: finding their endpoints in the API
schema, the Task Queue window, and the menus.

DearPyGui items can be built without a window, so these need only a context."""

from dataclasses import dataclass

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition import Experiment, Task
from pyacquisition.gui import Gui
from pyacquisition.gui.components.endpoint_popup import EndpointPopup
from pyacquisition.gui.components.task_manager_window import (
    ACCENT_WIDTH,
    GAP_BELOW_QUEUE,
    CARD_SPACING,
    X_ARROW_GAP,
    X_SIZE,
    TaskManagerWindow,
    format_value,
)
from pyacquisition.gui.constants import (
    QUEUED_ACCENT,
    QUEUED_BACKGROUND,
    DEFAULT_PAGE_WIDTH,
)
from pyacquisition.gui.managers import control_path, management_paths, task_paths
from pyacquisition.gui.openapi import Schema

MANAGEMENT = {
    "pause",
    "resume",
    "abort",
    "remove_task",
    "clear_tasks",
    "status",
    "current_task",
    "task_list",
}


@dataclass
class Hold(Task):
    """Hold the temperature."""

    kelvin: float = 4.2


# One experiment for the whole module. Each Experiment adds a subscriber to the global
# logger that is never removed, which slows every later log call, so do not make many.
@dataclass
class Tune(Task):
    """Change the gains."""

    kp: float = 1.0


@pytest.fixture(scope="module")
def experiment(tmp_path_factory):
    experiment = Experiment(root_path=str(tmp_path_factory.mktemp("gui")), gui=False)
    experiment.add_task_manager("control")
    experiment.register_task(Hold)  # on every task manager
    experiment.register_task(Tune, manager="control")  # on this one only
    for task_manager in experiment.task_managers.values():
        task_manager._register_endpoints(experiment._api_server)
    experiment._register_endpoints(experiment._api_server)
    return experiment


@pytest.fixture(scope="module")
def schema(experiment):
    return Schema(experiment._api_server.app.openapi())


@pytest.fixture
def gui_context(monkeypatch):
    dpg.create_context()
    monkeypatch.setattr(dpg, "get_viewport_client_height", lambda: 900)
    yield
    dpg.destroy_context()


def urls(paths):
    return {p.path for p in paths}


def descendants(item):
    for child in dpg.get_item_children(item, 1) or []:
        yield child
        yield from descendants(child)


def texts(item):
    return [
        dpg.get_value(child)
        for child in descendants(item)
        if dpg.get_item_type(child).endswith("mvText")
    ]


# ---------------------------------------------------------------------------
# Finding each task manager's endpoints
# ---------------------------------------------------------------------------


def test_the_main_manager_is_controlled_at_the_original_paths(schema):
    assert urls(management_paths(schema, "main")) == {
        f"/task_manager/{name}" for name in MANAGEMENT
    }


def test_the_main_manager_queues_tasks_at_the_original_paths(schema):
    assert urls(task_paths(schema, "main")) == {
        "/tasks/newfile",
        "/tasks/waitfor",
        "/tasks/waituntil",
        "/tasks/hold",
    }


def test_another_manager_has_its_own_paths(schema):
    assert urls(management_paths(schema, "control")) == {
        f"/managers/control/{name}" for name in MANAGEMENT
    }
    assert urls(task_paths(schema, "control")) == {
        "/managers/control/tasks/newfile",
        "/managers/control/tasks/waitfor",
        "/managers/control/tasks/waituntil",
        "/managers/control/tasks/hold",
        "/managers/control/tasks/tune",
    }


def test_the_managers_listing_and_snapshot_belong_to_none_of_them(schema):
    everything = urls(management_paths(schema, "main")) | urls(
        management_paths(schema, "control")
    )
    assert "/managers" not in everything
    assert "/managers/state" not in everything


@pytest.mark.parametrize("action", ["pause", "resume", "abort"])
def test_the_control_path_of_the_main_manager_is_the_original_one(schema, action):
    assert control_path("main", action) == f"/task_manager/{action}"
    assert control_path("main", action) in urls(management_paths(schema, "main"))


@pytest.mark.parametrize("action", ["pause", "resume", "abort"])
def test_the_control_path_of_another_manager_is_its_own(schema, action):
    assert control_path("control", action) == f"/managers/control/{action}"
    assert control_path("control", action) in urls(management_paths(schema, "control"))


def test_the_address_for_removing_a_queued_task(schema):
    assert (
        control_path("main", "remove_queued_task") == "/task_manager/remove_queued_task"
    )
    assert (
        control_path("control", "remove_queued_task")
        == "/managers/control/remove_queued_task"
    )


def test_the_address_for_moving_a_queued_task(schema):
    assert control_path("main", "move_queued_task") == "/task_manager/move_queued_task"
    assert (
        control_path("control", "move_queued_task")
        == "/managers/control/move_queued_task"
    )


def test_moving_a_queued_task_is_not_an_entry_in_the_menu(schema):
    for name in ("main", "control"):
        assert not any(
            path.endswith("move_queued_task")
            for path in urls(management_paths(schema, name))
        )


def test_removing_a_queued_task_is_not_an_entry_in_the_menu(schema):
    """The interface calls it from the buttons in the queue, so it is hidden."""
    for name in ("main", "control"):
        assert not any(
            path.endswith("remove_queued_task")
            for path in urls(management_paths(schema, name))
        )


def test_a_manager_called_state_is_not_confused_with_the_snapshot(tmp_path):
    experiment = Experiment(root_path=str(tmp_path), gui=False)
    experiment.add_task_manager("state")
    for task_manager in experiment.task_managers.values():
        task_manager._register_endpoints(experiment._api_server)
    experiment._register_endpoints(experiment._api_server)
    schema = Schema(experiment._api_server.app.openapi())

    assert urls(management_paths(schema, "state")) == {
        f"/managers/state/{name}" for name in MANAGEMENT
    }


# ---------------------------------------------------------------------------
# The Task Queue window
# ---------------------------------------------------------------------------

IDLE = {"status": "Running", "current_task": None, "queue": []}
RUNNING_TASK = {
    "name": "WaitFor",
    "description": "Wait for 0 hours, 5 minutes",
    "parameters": {"minutes": 5, "value": 37.3089118028939},
}
BUSY = {
    "status": "Running",
    "current_task": RUNNING_TASK,
    "queue": [
        {
            "name": "NewFile",
            "description": "Starting new file: after",
            "parameters": {"file_name": "after", "block": False},
        },
        {"name": "Hold", "description": "Hold it", "parameters": None},
    ],
}


def test_with_one_manager_the_window_has_a_header_and_the_queue(gui_context):
    window = TaskManagerWindow()
    panel = window.panels["main"]

    window.update({"main": BUSY})

    assert not any(
        dpg.get_item_type(item).endswith("mvCollapsingHeader")
        for item in descendants(window.window_tag)
    ), "There is no dropdown bar."
    header = panel.header
    assert (header.title, header.subtitle, header.badge, header.style) == (
        "Task Queue",
        "WaitFor",
        None,
        "idle",
    )
    assert not header.collapsible, "There is only one section to collapse."
    shown = texts(panel.queue_tag)
    assert "NewFile" in shown and "Hold" in shown
    assert "Starting new file: after" in shown


def test_with_several_managers_each_has_a_section_showing_its_state(gui_context):
    window = TaskManagerWindow(["main", "control"])

    window.update({"main": BUSY, "control": IDLE})

    main, control = window.panels["main"].header, window.panels["control"].header
    assert (main.title, main.subtitle, main.badge, main.style) == (
        "Main",
        "WaitFor",
        None,
        "idle",
    )
    assert (control.title, control.subtitle, control.badge, control.style) == (
        "Control",
        "nothing running",
        None,
        "idle",
    )


def test_each_section_shows_its_own_queue(gui_context):
    window = TaskManagerWindow(["main", "control"])

    window.update({"main": BUSY, "control": IDLE})

    main_texts = texts(window.panels["main"].queue_tag)
    control_texts = texts(window.panels["control"].queue_tag)
    assert "NewFile" in main_texts and "Hold" in main_texts
    assert control_texts == []


def test_a_section_follows_changes_in_its_manager(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": IDLE, "control": BUSY})

    window.update(
        {
            "main": IDLE,
            "control": {"status": "Paused", "current_task": None, "queue": []},
        }
    )

    control = window.panels["control"]
    assert (control.header.badge, control.header.style) == ("PAUSED", "paused")
    assert control.header.subtitle == "nothing running"
    assert texts(control.queue_tag) == []


def test_the_queue_is_not_rebuilt_when_nothing_has_changed(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})
    before = {name: panel.queue_tag for name, panel in window.panels.items()}

    window.update({"main": BUSY, "control": IDLE})
    unchanged = {name: panel.queue_tag for name, panel in window.panels.items()}
    window.update({"main": IDLE, "control": IDLE})
    changed = {name: panel.queue_tag for name, panel in window.panels.items()}

    assert unchanged == before
    assert changed["main"] != before["main"]
    assert changed["control"] == before["control"], "Only the manager that changed."


def test_a_manager_missing_from_the_update_is_left_alone(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY})  # no state for control: no error

    header = window.panels["control"].header
    assert header.title == "Control"
    assert header.badge is None, "It has not been given a state yet."


# --- the queue under each card ---


def spacers(item):
    """The heights of the gaps that are direct children of an item, in order."""
    return [
        dpg.get_item_configuration(child)["height"]
        for child in dpg.get_item_children(item, 1)
        if dpg.get_item_type(child).endswith("mvSpacer")
    ]


def test_a_queue_has_no_label_of_its_own(gui_context):
    """Nothing breaks up the active task from the tasks waiting behind it."""
    for names in (["main", "control"], ["main"]):
        window = TaskManagerWindow(names)
        window.update({"main": QUEUED, **({"control": IDLE} if len(names) > 1 else {})})

        shown = texts(window.panels["main"].queue_tag)

        assert "QUEUE" not in shown and "Queue:" not in texts(window.window_tag)
        assert not any("waiting" in t for t in shown)


def test_an_empty_queue_shows_nothing(gui_context):
    window = TaskManagerWindow(["main"])
    window.update({"main": IDLE})

    assert texts(window.panels["main"].queue_tag) == []
    assert "-" not in texts(window.window_tag)


def test_the_gap_below_a_queue_in_a_section_is_the_last_thing_in_the_section(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": QUEUED, "control": IDLE})
    panel = window.panels["main"]

    last = dpg.get_item_children(panel.section_tag, 1)[-1]

    assert dpg.get_item_type(last).endswith("mvSpacer")
    assert dpg.get_item_configuration(last)["height"] == GAP_BELOW_QUEUE


def test_with_one_manager_the_queue_has_no_gap_below_it(gui_context):
    window = TaskManagerWindow()

    window.update({"main": QUEUED})

    assert window.panels["main"].gap_tag is None


# --- the header of each task manager ---


def header_of(window, name):
    return window.panels[name].header


@pytest.mark.parametrize(
    "state, badge, style",
    [
        (IDLE, None, "idle"),
        (BUSY, None, "idle"),
        ({**BUSY, "status": "Paused"}, "PAUSED", "paused"),
        ({**IDLE, "status": "Paused"}, "PAUSED", "paused"),
        ({**BUSY, "status": "Paused", "aborting": True}, "ABORTING", "aborting"),
        ({**BUSY, "aborting": True}, "ABORTING", "aborting"),
    ],
)
def test_the_badge_and_colour_show_the_state(gui_context, state, badge, style):
    window = TaskManagerWindow(["main", "control"])

    window.update({"main": state, "control": IDLE})

    header = header_of(window, "main")
    assert (header.badge, header.style) == (badge, style)


def test_the_header_is_only_coloured_when_the_task_is_paused_or_aborting(gui_context):
    """Like the Live Data header, it is plain grey while all is well, and the card
    below it is the colour of the state."""
    window = TaskManagerWindow(["main", "control"])

    for state, style in (
        (BUSY, "idle"),
        ({**BUSY, "status": "Paused"}, "paused"),
        (ABORTING, "aborting"),
        (IDLE, "idle"),
    ):
        window.update({"main": state, "control": IDLE})
        assert window.panels["main"].header.style == style


def test_the_header_names_the_running_task(gui_context):
    window = TaskManagerWindow(["main", "control"])

    window.update({"main": BUSY, "control": IDLE})
    assert header_of(window, "main").subtitle == "WaitFor"

    window.update({"main": IDLE, "control": IDLE})
    assert header_of(window, "main").subtitle == "nothing running"


def test_the_names_of_the_task_managers_start_with_a_capital(gui_context):
    window = TaskManagerWindow(["main", "furnace_pid"])
    assert header_of(window, "furnace_pid").title == "Furnace_pid"


def test_the_window_has_no_title_bar_of_its_own(gui_context):
    window = TaskManagerWindow(["main", "control"])
    assert dpg.get_item_configuration(window.window_tag)["no_title_bar"] is True


def test_the_chevron_collapses_a_section_and_shows_it_again(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})
    main, control = window.panels["main"], window.panels["control"]

    main.header._toggle()

    assert main.header.collapsed
    assert dpg.get_item_configuration(main.section_tag)["show"] is False
    assert dpg.get_item_configuration(control.section_tag)["show"] is True, (
        "Only that one."
    )

    main.header._toggle()

    assert not main.header.collapsed
    assert dpg.get_item_configuration(main.section_tag)["show"] is True


def test_a_collapsed_section_still_shows_its_state_in_the_header(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})
    window.panels["control"].header._toggle()

    window.update({"main": BUSY, "control": {**BUSY, "status": "Paused"}})

    header = header_of(window, "control")
    assert (header.badge, header.subtitle) == ("PAUSED", "WaitFor")


def test_the_header_is_as_wide_as_the_window_allows(gui_context, monkeypatch):
    window = TaskManagerWindow(["main", "control"])
    header = header_of(window, "main")

    window.update({"main": IDLE, "control": IDLE})
    page = DEFAULT_PAGE_WIDTH  # there is no viewport to lay it out in
    assert header.width == page - 16, "The window's width less its padding."

    monkeypatch.setattr(dpg, "get_y_scroll_max", lambda item: 500)  # a scroll bar
    window.update({"main": IDLE, "control": IDLE})
    assert header.width == page - 16 - 14, "It must not make the window scroll sideways."

    monkeypatch.setattr(dpg, "get_y_scroll_max", lambda item: 0)
    window.update({"main": IDLE, "control": IDLE})
    assert header.width == page - 16


# --- the card that shows the active task ---


def card_texts(panel):
    return texts(panel.card_tag)


def card_colors(style):
    """The strip and the tint of the card of a state."""
    from pyacquisition.gui.constants import STATE_STYLES

    return STATE_STYLES[style]["border"], STATE_STYLES[style]["background"]


def test_the_active_task_is_shown_in_full_in_a_card(gui_context):
    window = TaskManagerWindow(["main", "control"])

    window.update({"main": BUSY, "control": IDLE})

    shown = card_texts(window.panels["main"])
    assert "RUNNING" in shown
    assert "WaitFor" in shown
    assert "Wait for 0 hours, 5 minutes" in shown
    assert "minutes" in [t.strip() for t in shown]
    assert "5" in [t.strip() for t in shown]


def test_long_decimals_are_shortened_in_the_card_and_the_queue(gui_context):
    window = TaskManagerWindow(["main", "control"])
    queued = {
        "name": "Hold",
        "description": "Hold it",
        "parameters": {"kelvin": 4.123456789},
    }

    window.update(
        {
            "main": {
                "status": "Running",
                "current_task": RUNNING_TASK,
                "queue": [queued],
            },
            "control": IDLE,
        }
    )

    main = window.panels["main"]
    assert "37.31" in [t.strip() for t in card_texts(main)]
    assert "4.123" in [t.strip() for t in texts(main.queue_tag)]


def test_the_card_is_green_while_running(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})

    panel = window.panels["main"]
    assert panel.card_style == "running"
    assert panel.card_colors == card_colors("running")


def test_the_card_is_amber_while_paused(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": {**BUSY, "status": "Paused"}, "control": IDLE})

    panel = window.panels["main"]
    assert panel.card_style == "paused"
    assert panel.card_colors == card_colors("paused")
    assert "PAUSED" in card_texts(panel)
    assert "RUNNING" not in card_texts(panel)


ABORTING = {**BUSY, "status": "Paused", "aborting": True}


def test_the_card_is_red_while_the_task_is_being_aborted(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": ABORTING, "control": IDLE})

    panel = window.panels["main"]
    assert panel.card_style == "aborting"
    assert panel.card_colors == card_colors("aborting")
    assert "ABORTING" in card_texts(panel)
    assert "PAUSED" not in card_texts(panel), "It is not just paused."


def test_the_card_goes_from_running_to_aborting_to_idle(gui_context):
    window = TaskManagerWindow(["main", "control"])
    panel = window.panels["main"]

    for state, style in [(BUSY, "running"), (ABORTING, "aborting"), (IDLE, "idle")]:
        window.update({"main": state, "control": IDLE})
        assert panel.card_style == style


def test_a_state_without_the_aborting_flag_is_not_aborting(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})  # BUSY has no such key
    assert window.panels["main"].card_style == "running"


def test_the_card_is_grey_when_nothing_is_running(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})

    control = window.panels["control"]
    assert control.card_style == "idle"
    assert control.card_colors == card_colors("idle")
    assert card_texts(control) == ["Idle: nothing is running"]


def test_an_idle_paused_task_manager_says_so(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update(
        {
            "main": IDLE,
            "control": {"status": "Paused", "current_task": None, "queue": []},
        }
    )

    control = window.panels["control"]
    assert control.card_style == "idle"
    assert card_texts(control) == ["Paused: nothing is running"]


def test_the_card_follows_the_task_through_its_states(gui_context):
    window = TaskManagerWindow(["main", "control"])
    panel = window.panels["main"]

    window.update({"main": IDLE, "control": IDLE})
    assert panel.card_style == "idle"
    window.update({"main": BUSY, "control": IDLE})
    assert panel.card_style == "running"
    window.update({"main": {**BUSY, "status": "Paused"}, "control": IDLE})
    assert panel.card_style == "paused"
    window.update({"main": BUSY, "control": IDLE})
    assert panel.card_style == "running"
    assert panel.card_colors == card_colors("running")


def test_the_card_shows_live_values_as_they_change(gui_context):
    window = TaskManagerWindow(["main", "control"])
    task = {"name": "PID", "description": "Hold 40", "parameters": {"value": 39.5}}
    window.update({"main": {**IDLE, "current_task": task}, "control": IDLE})
    panel = window.panels["main"]
    assert "39.5" in [t.strip() for t in card_texts(panel)]

    later = {**task, "parameters": {"value": 40.1}}
    window.update({"main": {**IDLE, "current_task": later}, "control": IDLE})

    shown = [t.strip() for t in card_texts(panel)]
    assert "40.1" in shown and "39.5" not in shown


def test_a_task_with_no_description_or_parameters_still_gets_a_card(gui_context):
    window = TaskManagerWindow(["main", "control"])
    bare = {"name": "Bare", "description": None, "parameters": None}

    window.update({"main": {**IDLE, "current_task": bare}, "control": IDLE})

    assert card_texts(window.panels["main"]) == ["RUNNING", "Bare"]


# --- the pause and resume icon in the header ---


def toggle_label(panel):
    """The icon in the header: `pause` offers to pause, and `play` to resume."""
    return panel.header.action


def press(panel):
    """Press the icon in the header, as a click would."""
    panel.header.on_action()


def test_the_button_offers_to_pause_a_running_task_manager(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})
    assert toggle_label(window.panels["main"]) == "pause"


def test_the_button_offers_to_resume_a_paused_task_manager(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": {**BUSY, "status": "Paused"}, "control": IDLE})
    assert toggle_label(window.panels["main"]) == "play"


def test_an_idle_task_manager_has_a_button_too(gui_context):
    """A paused queue with nothing running must still be resumable from the card."""
    window = TaskManagerWindow(["main", "control"])
    window.update(
        {
            "main": IDLE,
            "control": {"status": "Paused", "current_task": None, "queue": []},
        }
    )

    assert toggle_label(window.panels["main"]) == "pause"
    assert toggle_label(window.panels["control"]) == "play"


def test_the_button_follows_the_task_manager_between_pause_and_resume(gui_context):
    window = TaskManagerWindow(["main", "control"])
    panel = window.panels["main"]

    for status, label in [
        ("Running", "pause"),
        ("Paused", "play"),
        ("Running", "pause"),
    ]:
        window.update({"main": {**BUSY, "status": status}, "control": IDLE})
        assert toggle_label(panel) == label


def test_the_button_is_not_rebuilt_when_the_card_is_refreshed(gui_context):
    """The card is rebuilt as live values change. A button that was rebuilt with it
    could lose a click that straddled a refresh, so it must stay the same item."""
    window = TaskManagerWindow(["main", "control"])
    panel = window.panels["main"]
    window.update({"main": BUSY, "control": IDLE})
    button, title, body = panel.abort_tag, panel.title_tag, panel.body_tag

    for value in (1.0, 2.0, 3.0):
        task = {**RUNNING_TASK, "parameters": {"value": value}}
        window.update({"main": {**BUSY, "current_task": task}, "control": IDLE})

    assert panel.abort_tag == button
    assert dpg.does_item_exist(button)
    assert (panel.title_tag, panel.body_tag) == (title, body)
    assert "3" in [t.strip() for t in card_texts(panel)], "The card itself did refresh."


def test_pressing_the_button_reports_the_manager_and_whether_it_is_paused(gui_context):
    pressed = []
    window = TaskManagerWindow(
        ["main", "control"],
        on_toggle=lambda name, paused: pressed.append((name, paused)),
    )
    window.update({"main": BUSY, "control": {**BUSY, "status": "Paused"}})

    press(window.panels["main"])
    press(window.panels["control"])

    assert pressed == [("main", False), ("control", True)]


def test_pressing_the_button_does_nothing_if_nothing_is_listening(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})
    press(window.panels["main"])  # no error


# --- the remove buttons in the queue ---

QUEUE = [
    {
        "id": "id-a",
        "name": "NewFile",
        "description": "Start a file",
        "parameters": None,
    },
    {
        "id": "id-b",
        "name": "Hold",
        "description": "Hold it",
        "parameters": {"kelvin": 4.2},
    },
]
QUEUED = {"status": "Running", "current_task": RUNNING_TASK, "queue": QUEUE}


def window_with_remove(names=("main", "control"), **options):
    pressed = []
    window = TaskManagerWindow(
        list(names), on_remove=lambda *args: pressed.append(args), **options
    )
    return window, pressed


def press_remove(panel, task_id):
    button = panel.remove_tags[task_id]
    dpg.get_item_callback(button)(button, None, dpg.get_item_user_data(button))


def test_each_queued_task_has_a_remove_button(gui_context):
    window, _ = window_with_remove()

    window.update({"main": QUEUED, "control": IDLE})

    panel = window.panels["main"]
    assert set(panel.remove_tags) == {"id-a", "id-b"}
    for button in panel.remove_tags.values():
        assert dpg.get_item_label(button) == "X"
        assert dpg.get_item_theme(button) == window.panels["main"]._x_theme


def test_an_empty_queue_has_no_remove_buttons(gui_context):
    window, _ = window_with_remove()
    window.update({"main": QUEUED, "control": IDLE})
    window.update({"main": IDLE, "control": IDLE})
    assert window.panels["main"].remove_tags == {}


def test_pressing_remove_reports_the_manager_the_id_and_the_name(gui_context):
    window, pressed = window_with_remove()
    window.update({"main": QUEUED, "control": {**QUEUED, "queue": [QUEUE[1]]}})

    press_remove(window.panels["main"], "id-a")
    press_remove(window.panels["control"], "id-b")

    assert pressed == [("main", "id-a", "NewFile"), ("control", "id-b", "Hold")]


def test_each_button_removes_its_own_task_even_when_the_names_match(gui_context):
    window, pressed = window_with_remove()
    twin_a = {"id": "one", "name": "Hold", "description": None, "parameters": None}
    twin_b = {"id": "two", "name": "Hold", "description": None, "parameters": None}
    window.update({"main": {**QUEUED, "queue": [twin_a, twin_b]}, "control": IDLE})

    press_remove(window.panels["main"], "two")

    assert pressed == [("main", "two", "Hold")]


def test_a_queued_task_without_an_id_gets_no_button(gui_context):
    window, _ = window_with_remove()
    no_id = {"name": "Old", "description": None, "parameters": None}

    window.update({"main": {**QUEUED, "queue": [no_id, QUEUE[0]]}, "control": IDLE})

    assert set(window.panels["main"].remove_tags) == {"id-a"}


def test_there_are_no_remove_buttons_if_nothing_is_listening(gui_context):
    window = TaskManagerWindow(["main", "control"])  # no on_remove

    window.update({"main": QUEUED, "control": IDLE})

    assert window.panels["main"].remove_tags == {}


def test_with_one_manager_the_queue_has_remove_buttons_too(gui_context):
    window, pressed = window_with_remove(names=("main",))

    window.update({"main": QUEUED})

    assert set(window.panels["main"].remove_tags) == {"id-a", "id-b"}
    press_remove(window.panels["main"], "id-b")
    assert pressed == [("main", "id-b", "Hold")]


def test_the_queue_is_not_rebuilt_as_the_running_tasks_values_change(gui_context):
    """The card refreshes every second for a PID. Rebuilding the queue with it would
    recreate the remove buttons, and could lose a click that straddled a refresh."""
    window, _ = window_with_remove()
    window.update({"main": QUEUED, "control": IDLE})
    panel = window.panels["main"]
    buttons = dict(panel.remove_tags)
    queue_tag = panel.queue_tag

    for value in (1.0, 2.0, 3.0):
        task = {**RUNNING_TASK, "parameters": {"value": value}}
        window.update({"main": {**QUEUED, "current_task": task}, "control": IDLE})

    assert panel.remove_tags == buttons
    assert panel.queue_tag == queue_tag
    assert all(dpg.does_item_exist(button) for button in buttons.values())
    assert "3" in [t.strip() for t in card_texts(panel)], "The card itself did refresh."


def test_the_queue_is_rebuilt_when_a_task_leaves_it(gui_context):
    window, _ = window_with_remove()
    window.update({"main": QUEUED, "control": IDLE})
    panel = window.panels["main"]

    window.update({"main": {**QUEUED, "queue": [QUEUE[1]]}, "control": IDLE})

    assert set(panel.remove_tags) == {"id-b"}


# --- the arrows that move a queued task ---

THREE = [
    {"id": "id-a", "name": "First", "description": None, "parameters": None},
    {"id": "id-b", "name": "Second", "description": None, "parameters": None},
    {"id": "id-c", "name": "Third", "description": None, "parameters": None},
]
THREE_QUEUED = {"status": "Running", "current_task": RUNNING_TASK, "queue": THREE}


def window_with_move(names=("main", "control")):
    moved = []
    window = TaskManagerWindow(list(names), on_move=lambda *args: moved.append(args))
    return window, moved


def arrows(panel, task_id):
    up, down = panel.move_tags[task_id]
    return up, down


def enabled(item):
    return dpg.get_item_configuration(item)["enabled"]


def press_arrow(panel, task_id, direction):
    up, down = arrows(panel, task_id)
    button = up if direction == "up" else down
    dpg.get_item_callback(button)(button, None, dpg.get_item_user_data(button))


def test_each_queued_task_has_an_up_and_a_down_arrow(gui_context):
    window, _ = window_with_move()

    window.update({"main": THREE_QUEUED, "control": IDLE})

    panel = window.panels["main"]
    assert set(panel.move_tags) == {"id-a", "id-b", "id-c"}
    for up, down in panel.move_tags.values():
        assert dpg.get_item_configuration(up)["direction"] == dpg.mvDir_Up
        assert dpg.get_item_configuration(down)["direction"] == dpg.mvDir_Down


def test_the_first_task_cannot_go_up_because_that_place_is_the_running_tasks(gui_context):
    window, _ = window_with_move()

    window.update({"main": THREE_QUEUED, "control": IDLE})

    up, down = arrows(window.panels["main"], "id-a")
    assert not enabled(up), "The place in front of it is the running task's."
    assert enabled(down)


def test_the_last_task_cannot_go_down(gui_context):
    window, _ = window_with_move()

    window.update({"main": THREE_QUEUED, "control": IDLE})

    up, down = arrows(window.panels["main"], "id-c")
    assert enabled(up)
    assert not enabled(down)


def test_a_task_in_the_middle_can_go_either_way(gui_context):
    window, _ = window_with_move()

    window.update({"main": THREE_QUEUED, "control": IDLE})

    up, down = arrows(window.panels["main"], "id-b")
    assert enabled(up) and enabled(down)


def test_the_arrows_have_a_faint_look_for_when_they_cannot_be_used(gui_context):
    window, _ = window_with_move()
    window.update({"main": THREE_QUEUED, "control": IDLE})
    panel = window.panels["main"]

    for task_id in ("id-a", "id-b", "id-c"):
        for button in arrows(panel, task_id):
            assert dpg.get_item_theme(button) == panel._arrow_theme


def test_a_task_on_its_own_cannot_go_either_way(gui_context):
    window, _ = window_with_move()

    window.update({"main": {**QUEUED, "queue": QUEUE[:1]}, "control": IDLE})

    up, down = arrows(window.panels["main"], "id-a")
    assert not enabled(up) and not enabled(down)


def test_the_arrows_are_updated_when_the_queue_changes(gui_context):
    window, _ = window_with_move()
    window.update({"main": THREE_QUEUED, "control": IDLE})
    assert enabled(arrows(window.panels["main"], "id-b")[0])

    # The first task has started, so the second is now at the front.
    window.update({"main": {**THREE_QUEUED, "queue": THREE[1:]}, "control": IDLE})

    up, down = arrows(window.panels["main"], "id-b")
    assert not enabled(up), "It is at the front now, so it cannot go up."
    assert enabled(down)
    assert "id-a" not in window.panels["main"].move_tags


def test_pressing_an_arrow_reports_the_manager_the_task_and_the_direction(gui_context):
    window, moved = window_with_move()
    window.update({"main": THREE_QUEUED, "control": {**THREE_QUEUED, "queue": THREE[:2]}})

    press_arrow(window.panels["main"], "id-b", "up")
    press_arrow(window.panels["main"], "id-b", "down")
    press_arrow(window.panels["control"], "id-a", "down")

    assert moved == [
        ("main", "id-b", "Second", "up"),
        ("main", "id-b", "Second", "down"),
        ("control", "id-a", "First", "down"),
    ]


def test_the_first_task_cannot_be_moved_up_even_if_the_handler_is_called(gui_context):
    """A greyed out button does not fire, but the handler must hold on its own."""
    window, moved = window_with_move()
    window.update({"main": THREE_QUEUED, "control": IDLE})

    press_arrow(window.panels["main"], "id-a", "up")

    assert moved == []


def test_the_last_task_cannot_be_moved_down_even_if_the_handler_is_called(gui_context):
    window, moved = window_with_move()
    window.update({"main": THREE_QUEUED, "control": IDLE})

    press_arrow(window.panels["main"], "id-c", "down")

    assert moved == []


def test_a_task_that_has_left_the_queue_is_not_moved(gui_context):
    window, moved = window_with_move()
    window.update({"main": THREE_QUEUED, "control": IDLE})
    panel = window.panels["main"]
    stale_up, _ = arrows(panel, "id-b")
    user_data = dpg.get_item_user_data(stale_up)
    callback = dpg.get_item_callback(stale_up)

    window.update({"main": {**THREE_QUEUED, "queue": [THREE[0], THREE[2]]}, "control": IDLE})
    callback(stale_up, None, user_data)  # a click on a button from a moment ago

    assert moved == []


def test_there_are_no_arrows_if_nothing_is_listening(gui_context):
    window = TaskManagerWindow(["main", "control"])  # no on_move
    window.update({"main": THREE_QUEUED, "control": IDLE})
    assert window.panels["main"].move_tags == {}


def test_a_queued_task_without_an_id_gets_no_arrows(gui_context):
    window, _ = window_with_move()
    no_id = {"name": "Old", "description": None, "parameters": None}

    window.update({"main": {**QUEUED, "queue": [no_id, QUEUE[0]]}, "control": IDLE})

    assert set(window.panels["main"].move_tags) == {"id-a"}


def test_the_arrows_are_one_above_the_other_under_the_remove_button(gui_context):
    window = TaskManagerWindow(
        ["main", "control"], on_move=lambda *a: None, on_remove=lambda *a: None
    )
    window.update({"main": THREE_QUEUED, "control": IDLE})

    panel = window.panels["main"]
    up, down = arrows(panel, "id-b")
    remove = panel.remove_tags["id-b"]
    assert dpg.get_item_parent(up) == dpg.get_item_parent(down)
    for button in (up, down):
        assert dpg.get_item_configuration(button)["width"] == X_SIZE, "One column."
    assert dpg.get_item_configuration(up)["direction"] == dpg.mvDir_Up
    assert dpg.get_item_configuration(down)["direction"] == dpg.mvDir_Down
    column = dpg.get_item_parent(remove)
    below = dpg.get_item_children(column, 1)
    assert below[0] == remove and below[-1] == dpg.get_item_parent(up)
    (gap,) = [i for i in below[1:-1]]
    assert dpg.get_item_type(gap).endswith("mvSpacer")
    assert dpg.get_item_configuration(gap)["height"] == X_ARROW_GAP > 0
    assert dpg.get_item_children(dpg.get_item_parent(up), 1) == [up, down]


def test_a_line_under_the_active_card_matches_the_one_under_the_header(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})
    panel = window.panels["main"]

    children = dpg.get_item_children(panel.section_tag, 1)
    assert children.index(panel._rule_list) == children.index(panel.card_tag) + 1
    assert dpg.get_item_configuration(panel._rule_list)["height"] == 1
    assert dpg.get_item_configuration(panel._rule_list)["width"] == panel.header.width
    grey = dpg.get_item_configuration(panel._rule)["color"]
    assert grey == dpg.get_item_configuration(panel.header._rule)["color"]

    window.update({"main": {**BUSY, "status": "Paused"}, "control": IDLE})
    assert dpg.get_item_configuration(panel._rule)["color"] != grey
    assert dpg.get_item_configuration(panel._rule)["color"] == (
        dpg.get_item_configuration(panel.header._rule)["color"]
    )


def test_the_queue_is_empty_of_arrows_when_nothing_is_waiting(gui_context):
    window, _ = window_with_move()
    window.update({"main": THREE_QUEUED, "control": IDLE})
    window.update({"main": IDLE, "control": IDLE})
    assert window.panels["main"].move_tags == {}


def test_with_one_manager_the_queue_has_arrows_too(gui_context):
    window, moved = window_with_move(names=("main",))

    window.update({"main": THREE_QUEUED})
    press_arrow(window.panels["main"], "id-b", "up")

    assert moved == [("main", "id-b", "Second", "up")]


def test_the_arrows_are_not_rebuilt_as_the_running_tasks_values_change(gui_context):
    """The card refreshes every second for a PID. Recreating the arrows with it could
    lose a click that straddled a refresh."""
    window, _ = window_with_move()
    window.update({"main": THREE_QUEUED, "control": IDLE})
    panel = window.panels["main"]
    before = dict(panel.move_tags)

    for value in (1.0, 2.0, 3.0):
        task = {**RUNNING_TASK, "parameters": {"value": value}}
        window.update({"main": {**THREE_QUEUED, "current_task": task}, "control": IDLE})

    assert panel.move_tags == before
    assert all(dpg.does_item_exist(b) for pair in before.values() for b in pair)


# --- the abort button on the card ---


def abort_enabled(panel):
    return dpg.get_item_configuration(panel.abort_tag)["enabled"]


def press_abort(panel):
    dpg.get_item_callback(panel.abort_tag)(panel.abort_tag, None, None)


def test_the_abort_button_is_a_red_square_with_an_x(gui_context):
    window = TaskManagerWindow(["main", "control"])
    panel = window.panels["main"]
    config = dpg.get_item_configuration(panel.abort_tag)
    assert dpg.get_item_label(panel.abort_tag) == "X"
    assert config["width"] == config["height"], "A square."
    assert dpg.get_item_theme(panel.abort_tag) == panel._x_theme


def test_the_abort_button_works_while_a_task_is_running_or_paused(gui_context):
    window = TaskManagerWindow(["main", "control"])

    window.update({"main": BUSY, "control": {**BUSY, "status": "Paused"}})

    assert abort_enabled(window.panels["main"])
    assert abort_enabled(window.panels["control"])


def test_the_abort_button_is_disabled_once_the_task_is_being_aborted(gui_context):
    window = TaskManagerWindow(["main", "control"])

    window.update({"main": ABORTING, "control": IDLE})

    assert not abort_enabled(window.panels["main"])


def test_pressing_abort_while_it_is_being_aborted_does_nothing(gui_context):
    pressed = []
    window = TaskManagerWindow(
        ["main", "control"], on_abort=lambda *a: pressed.append(a)
    )
    window.update({"main": ABORTING, "control": IDLE})

    press_abort(window.panels["main"])

    assert pressed == []


def test_the_abort_button_is_disabled_when_nothing_is_running(gui_context):
    window = TaskManagerWindow(["main", "control"])

    window.update({"main": BUSY, "control": IDLE})

    assert abort_enabled(window.panels["main"])
    assert not abort_enabled(window.panels["control"])


def test_the_abort_button_follows_whether_a_task_is_running(gui_context):
    window = TaskManagerWindow(["main", "control"])
    panel = window.panels["main"]

    for state, enabled in [(IDLE, False), (BUSY, True), (IDLE, False)]:
        window.update({"main": state, "control": IDLE})
        assert abort_enabled(panel) == enabled


def test_pressing_abort_reports_the_manager_and_the_task(gui_context):
    pressed = []
    window = TaskManagerWindow(
        ["main", "control"], on_abort=lambda name, task: pressed.append((name, task))
    )
    window.update({"main": BUSY, "control": IDLE})

    press_abort(window.panels["main"])

    assert pressed == [("main", "WaitFor")]


def test_pressing_abort_with_nothing_running_does_nothing(gui_context):
    pressed = []
    window = TaskManagerWindow(
        ["main", "control"], on_abort=lambda *a: pressed.append(a)
    )
    window.update({"main": IDLE, "control": IDLE})

    press_abort(window.panels["control"])

    assert pressed == []


def test_pressing_abort_does_nothing_if_nothing_is_listening(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": BUSY, "control": IDLE})
    press_abort(window.panels["main"])  # no error


def test_the_abort_button_is_not_rebuilt_when_the_card_is_refreshed(gui_context):
    window = TaskManagerWindow(["main", "control"])
    panel = window.panels["main"]
    window.update({"main": BUSY, "control": IDLE})
    button = panel.abort_tag

    for value in (1.0, 2.0, 3.0):
        task = {**RUNNING_TASK, "parameters": {"value": value}}
        window.update({"main": {**BUSY, "current_task": task}, "control": IDLE})

    assert panel.abort_tag == button and dpg.does_item_exist(button)


# --- with one task manager, the running task is shown in full too ---


def test_with_one_manager_the_running_task_is_shown_in_full(gui_context):
    """It used to be in the header only: its name, and nothing of what it was doing."""
    window = TaskManagerWindow()
    window.update({"main": BUSY})

    shown = [t.strip() for t in card_texts(window.panels["main"])]

    assert "WaitFor" in shown
    assert "Wait for 0 hours, 5 minutes" in shown, "its description"
    assert {"minutes", "5", "value", "37.31"} <= set(shown), "and its inputs"


def test_with_one_manager_the_card_is_coloured_by_the_state(gui_context):
    window = TaskManagerWindow()
    panel = window.panels["main"]

    window.update({"main": BUSY})
    assert panel.card_colors == card_colors("running")

    window.update({"main": {**BUSY, "status": "Paused"}})
    assert panel.card_colors == card_colors("paused")

    window.update({"main": IDLE})
    assert panel.card_colors == card_colors("idle")
    assert "Idle: nothing is running" in [t.strip() for t in card_texts(panel)]


def test_with_one_manager_the_header_has_pause_and_the_card_abort(gui_context):
    pressed = []
    window = TaskManagerWindow(
        on_toggle=lambda name, paused: pressed.append(("toggle", name, paused)),
        on_abort=lambda name, task: pressed.append(("abort", name, task)),
    )
    window.update({"main": BUSY})
    panel = window.panels["main"]

    press(panel)
    dpg.get_item_callback(panel.abort_tag)(panel.abort_tag, None, None)

    assert pressed == [("toggle", "main", False), ("abort", "main", "WaitFor")]
    assert panel.header.action == "pause"


def test_with_one_manager_the_header_is_not_collapsible(gui_context):
    window = TaskManagerWindow()

    assert not window.panels["main"].header.collapsible


@pytest.mark.parametrize(
    "value, shown",
    [
        (37.3089118028939, "37.31"),
        (0.5, "0.5"),
        (2.0, "2"),
        (1e-7, "1e-07"),
        (5, "5"),
        ("x", "x"),
        (True, "True"),
        (None, "None"),
    ],
)
def test_format_value(value, shown):
    assert format_value(value) == shown


def test_the_window_fills_the_height_of_the_viewport(gui_context):
    window = TaskManagerWindow(["main", "control"])
    window.update({"main": IDLE, "control": IDLE})
    assert dpg.get_item_configuration(window.window_tag)["height"] == 900 - 40


# ---------------------------------------------------------------------------
# Discovering the managers
# ---------------------------------------------------------------------------


def test_the_gui_asks_the_api_for_the_task_managers():
    gui = Gui()
    gui.api_client.get = lambda endpoint, **kw: {
        "status": 200,
        "data": ["main", "control"],
    }
    assert gui._fetch_task_managers() == ["main", "control"]


def test_the_gui_falls_back_to_just_the_main_manager():
    gui = Gui()

    def fail(endpoint, **kw):
        raise ConnectionError("no server")

    gui.api_client.get = fail
    assert gui._fetch_task_managers() == ["main"]

    gui.api_client.get = lambda endpoint, **kw: {"status": 200, "data": []}
    assert gui._fetch_task_managers() == ["main"]


# ---------------------------------------------------------------------------
# What pressing the button does
# ---------------------------------------------------------------------------


class RecordingClient:
    """Stands in for the API client."""

    def __init__(self, states=None, fail_on=None):
        self.requests = []
        self.params = []
        self.states = states or {}
        self.fail_on = fail_on

    def get(self, endpoint, params=None, callback=None, timeout=None):
        self.requests.append((endpoint, timeout))
        self.params.append(params)
        if endpoint == self.fail_on:
            raise ConnectionError("no server")
        if endpoint == "/managers/state":
            return {"status": 200, "data": self.states}
        return {"status": "success"}


class RecordingWindow:
    def __init__(self):
        self.updates = []

    def update(self, states):
        self.updates.append(states)


def make_gui(client):
    gui = Gui()
    gui.api_client = client
    gui.task_window = RecordingWindow()
    return gui


def test_pressing_pause_pauses_that_task_manager_and_refreshes_at_once():
    states = {"main": IDLE}
    gui = make_gui(RecordingClient(states))

    gui._toggle_task_manager("control", paused=False)

    assert [endpoint for endpoint, _ in gui.api_client.requests] == [
        "/managers/control/pause",
        "/managers/state",
    ]
    assert gui.task_window.updates == [states]


def test_pressing_resume_resumes_it():
    gui = make_gui(RecordingClient({"main": IDLE}))

    gui._toggle_task_manager("main", paused=True)

    assert gui.api_client.requests[0][0] == "/task_manager/resume"


def test_the_requests_have_a_timeout_so_a_stuck_server_cannot_freeze_the_window():
    gui = make_gui(RecordingClient({"main": IDLE}))
    gui._toggle_task_manager("main", paused=False)
    assert all(timeout for _, timeout in gui.api_client.requests)


def test_a_failed_request_is_logged_and_does_not_raise():
    gui = make_gui(RecordingClient(fail_on="/managers/control/pause"))

    gui._toggle_task_manager("control", paused=False)  # no error

    assert gui.task_window.updates == [], "Nothing to show if it did not work."


def test_the_api_client_passes_its_timeout_on(monkeypatch):
    import pyacquisition.gui.api_client as api_client_module

    seen = {}

    class Response:
        def json(self):
            return {"ok": True}

    def fake_get(url, params=None, timeout=None):
        seen.update(url=url, timeout=timeout)
        return Response()

    monkeypatch.setattr(api_client_module.requests, "get", fake_get)
    client = api_client_module.APIClient(host="localhost", port=1234)

    client.get("/managers/state", timeout=5)

    assert seen == {"url": "http://localhost:1234/managers/state", "timeout": 5}


# ---------------------------------------------------------------------------
# Aborting asks first
# ---------------------------------------------------------------------------


def popup_windows():
    return [
        item
        for item in dpg.get_all_items()
        if dpg.get_item_type(item).endswith("mvWindowAppItem")
        and dpg.get_item_configuration(item)["modal"]
    ]


def answer(popup, button):
    dpg.get_item_callback(button)(button, None, None)


@pytest.fixture
def asking(gui_context, monkeypatch):
    """A GUI that can show popups, with a size for the window."""
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1000)
    return make_gui(RecordingClient({"main": IDLE}))


def test_aborting_shows_a_popup_and_sends_nothing_yet(asking):
    asking._abort_task_manager("control", "furnace PID")

    assert len(popup_windows()) == 1
    assert asking.api_client.requests == []


def test_the_popup_says_what_will_be_aborted_and_what_follows(asking):
    asking._abort_task_manager("control", "furnace PID")

    popup = asking._confirmations["control"]
    shown = " ".join(
        dpg.get_value(child)
        for child in dpg.get_item_children(popup.tag, 1)
        if dpg.get_item_type(child).endswith("mvText")
    )
    assert dpg.get_item_label(popup.tag) == "Abort furnace PID?"
    assert "furnace PID" in shown and "control" in shown
    assert "teardown" in shown and "Resume" in shown
    assert dpg.get_item_label(popup.confirm_tag) == "Abort"
    assert dpg.get_item_theme(popup.confirm_tag), "It is a dangerous action."


def test_confirming_aborts_that_task_manager_and_refreshes_at_once(asking):
    asking._abort_task_manager("control", "furnace PID")
    popup = asking._confirmations["control"]

    answer(popup, popup.confirm_tag)

    assert [endpoint for endpoint, _ in asking.api_client.requests] == [
        "/managers/control/abort",
        "/managers/state",
    ]
    assert asking.task_window.updates == [{"main": IDLE}]
    assert popup_windows() == []


def test_the_main_manager_is_aborted_at_its_original_address(asking):
    asking._abort_task_manager("main", "WaitFor")
    popup = asking._confirmations["main"]

    answer(popup, popup.confirm_tag)

    assert asking.api_client.requests[0][0] == "/task_manager/abort"


def test_cancelling_sends_nothing(asking):
    asking._abort_task_manager("control", "furnace PID")
    popup = asking._confirmations["control"]

    answer(popup, popup.cancel_tag)

    assert asking.api_client.requests == []
    assert popup_windows() == []


def test_pressing_abort_again_while_asking_does_not_stack_popups(asking):
    asking._abort_task_manager("control", "furnace PID")
    asking._abort_task_manager("control", "furnace PID")

    assert len(popup_windows()) == 1


def test_it_can_ask_again_after_it_was_answered(asking):
    asking._abort_task_manager("control", "furnace PID")
    first = asking._confirmations["control"]
    answer(first, first.cancel_tag)

    asking._abort_task_manager("control", "furnace PID")

    assert len(popup_windows()) == 1
    assert asking._confirmations["control"] is not first


def test_two_task_managers_can_each_be_asking(asking):
    asking._abort_task_manager("control", "furnace PID")
    asking._abort_task_manager("main", "WaitFor")

    assert len(popup_windows()) == 2


def test_a_failed_abort_is_logged_and_does_not_raise(gui_context, monkeypatch):
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1000)
    gui = make_gui(RecordingClient(fail_on="/managers/control/abort"))
    gui._abort_task_manager("control", "furnace PID")
    popup = gui._confirmations["control"]

    answer(popup, popup.confirm_tag)  # no error

    assert popup_windows() == []


# ---------------------------------------------------------------------------
# What pressing a remove button does
# ---------------------------------------------------------------------------


def test_removing_a_queued_task_sends_its_id_and_refreshes_at_once():
    states = {"main": IDLE}
    gui = make_gui(RecordingClient(states))

    gui._remove_queued_task("control", "id-b", "Hold")

    assert [endpoint for endpoint, _ in gui.api_client.requests] == [
        "/managers/control/remove_queued_task",
        "/managers/state",
    ]
    assert gui.api_client.params[0] == {"task_id": "id-b"}
    assert gui.task_window.updates == [states]


def test_a_task_is_removed_from_the_main_manager_at_its_original_address():
    gui = make_gui(RecordingClient({"main": IDLE}))

    gui._remove_queued_task("main", "id-a", "NewFile")

    assert gui.api_client.requests[0][0] == "/task_manager/remove_queued_task"


def test_removing_a_task_does_not_ask_first_and_has_a_timeout():
    gui = make_gui(RecordingClient({"main": IDLE}))

    gui._remove_queued_task("main", "id-a", "NewFile")

    assert gui._confirmations == {}, "No popup: it is one click."
    assert all(timeout for _, timeout in gui.api_client.requests)


def test_a_failed_removal_is_logged_and_does_not_raise():
    gui = make_gui(RecordingClient(fail_on="/managers/control/remove_queued_task"))

    gui._remove_queued_task("control", "id-b", "Hold")  # no error

    assert gui.task_window.updates == []


def test_the_other_actions_send_no_parameters():
    gui = make_gui(RecordingClient({"main": IDLE}))

    gui._toggle_task_manager("main", paused=False)

    assert gui.api_client.params[0] is None


# ---------------------------------------------------------------------------
# What pressing an arrow does
# ---------------------------------------------------------------------------


def test_moving_a_queued_task_sends_its_id_and_the_direction_and_refreshes():
    states = {"main": IDLE}
    gui = make_gui(RecordingClient(states))

    gui._move_queued_task("control", "id-b", "Second", "up")

    assert [endpoint for endpoint, _ in gui.api_client.requests] == [
        "/managers/control/move_queued_task",
        "/managers/state",
    ]
    assert gui.api_client.params[0] == {"task_id": "id-b", "direction": "up"}
    assert gui.task_window.updates == [states]


def test_a_task_is_moved_in_the_main_manager_at_its_original_address():
    gui = make_gui(RecordingClient({"main": IDLE}))

    gui._move_queued_task("main", "id-a", "First", "down")

    assert gui.api_client.requests[0][0] == "/task_manager/move_queued_task"
    assert gui.api_client.params[0]["direction"] == "down"


def test_moving_a_task_does_not_ask_first_and_has_a_timeout():
    gui = make_gui(RecordingClient({"main": IDLE}))

    gui._move_queued_task("main", "id-a", "First", "up")

    assert gui._confirmations == {}, "No popup: it is one click, and easily undone."
    assert all(timeout for _, timeout in gui.api_client.requests)


def test_a_failed_move_is_logged_and_does_not_raise():
    gui = make_gui(RecordingClient(fail_on="/managers/control/move_queued_task"))

    gui._move_queued_task("control", "id-b", "Second", "up")  # no error

    assert gui.task_window.updates == []



# --- a queued task is a grey card with a bold edge, with its lines packed close ---


def ancestors(item):
    while item:
        yield item
        item = dpg.get_item_parent(item)


def queued_window(*tasks, **options):
    window = TaskManagerWindow(["main"], **options)
    window.update({"main": {"status": "Running", "current_task": None, "queue": list(tasks)}})
    return window


def task(id_, name="Hold", description="Hold it", parameters=None):
    return {"id": id_, "name": name, "description": description, "parameters": parameters}


def test_each_queued_task_is_a_card(gui_context):
    window = queued_window(task("a"), task("b"), task("c"))

    panel = window.panels["main"]

    assert len(panel.card_tags) == 3
    for card in panel.card_tags:
        assert dpg.get_item_type(card).endswith("mvTable")
        assert dpg.get_item_parent(card) == panel.queue_tag


def test_a_card_has_a_bold_edge_at_its_left_and_a_grey_background(gui_context, monkeypatch):
    """The edge and the background are the two cells of the card, coloured."""
    coloured = []
    monkeypatch.setattr(dpg, "highlight_table_cell", lambda *args: coloured.append(args))

    window = queued_window(task("a"))

    (card,) = window.panels["main"].card_tags
    assert [c for c in coloured if c[0] == card] == [
        (card, 0, 0, QUEUED_ACCENT),
        (card, 0, 1, QUEUED_BACKGROUND),
    ]
    edge, body = dpg.get_item_children(card, 0)
    assert dpg.get_item_configuration(edge)["width_fixed"] is True
    assert dpg.get_item_configuration(edge)["init_width_or_weight"] == ACCENT_WIDTH
    assert dpg.get_item_configuration(body)["width_stretch"] is True


def test_the_edge_is_as_bold_as_the_accent_of_a_header_and_blue():
    """As thick as a header's edge, and a brighter blue than the card."""
    assert ACCENT_WIDTH == 5
    r, g, b = QUEUED_ACCENT
    assert b > r and b > g, "Blue."
    assert b > QUEUED_BACKGROUND[2] + 60, "Brighter than the card, so that it shows."


def test_the_background_is_a_dark_blue():
    r, g, b = QUEUED_BACKGROUND
    assert b > r and 20 < b < 70, "Blue, and lighter than the window."


def test_a_queued_card_is_blue_and_the_active_card_is_green(gui_context):
    window = queued_window(task("a"))
    window.update(
        {"main": {**BUSY, "queue": [task("a")]}}
    )
    panel = window.panels["main"]

    assert panel.card_colors == card_colors("running")
    assert panel.card_colors[0][1] > panel.card_colors[0][0], "Green."
    assert QUEUED_ACCENT[2] > QUEUED_ACCENT[1] > QUEUED_ACCENT[0], "Blue."


def test_the_header_is_flat_with_a_white_title(gui_context):
    window = TaskManagerWindow(["main"])
    header = window.panels["main"].header

    assert header.flat
    assert dpg.get_item_configuration(header._accent)["show"] is False
    assert dpg.get_item_configuration(header._rule)["show"] is True


def test_the_text_of_a_task_is_in_its_card(gui_context):
    window = queued_window(
        task("a", "SetTemperature", "Ramp and hold.", {"kelvin": 4.5, "hold": 600})
    )

    (card,) = window.panels["main"].card_tags

    shown = [t.strip() for t in texts(card)]
    assert {"[0]", "SetTemperature", "Ramp and hold.", "kelvin", "4.5", "hold", "600"} <= set(shown)


def test_the_buttons_of_a_task_are_in_its_card(gui_context):
    window, _ = window_with_remove(names=("main",), on_move=lambda *a: None)
    window.update({"main": QUEUED})

    panel = window.panels["main"]
    for card, (task_id, remove) in zip(panel.card_tags, panel.remove_tags.items()):
        assert card in ancestors(remove)
        up, down = panel.move_tags[task_id]
        assert card in ancestors(up) and card in ancestors(down)


def test_the_lines_of_a_card_are_packed_close(gui_context):
    """Four pixels apart is the default. It took too much room in a long queue."""
    window = queued_window(task("a", parameters={"kelvin": 4.5}))
    panel = window.panels["main"]
    (card,) = panel.card_tags

    theme = dpg.get_item_theme(card)
    (component,) = dpg.get_item_children(theme, 1)
    styles = [list(dpg.get_value(i)) for i in dpg.get_item_children(component, 1)]

    assert theme == panel._card_theme
    assert [6.0, 1.0] in styles, "The lines are one pixel apart."
    assert [0.0, 0.0] in styles, "The cells have no padding, so the colour fills them."


def test_the_cards_are_as_close_together_as_in_the_live_data_window(gui_context):
    window = queued_window(task("a"), task("b"))

    assert spacers(window.panels["main"].queue_tag) == [], "Only the spacing between."
    component = dpg.get_item_children(window._spacing_theme, 1)[0]
    (spacing,) = dpg.get_item_children(component, 1)
    assert list(dpg.get_value(spacing))[:2] == [6.0, float(CARD_SPACING)]
    assert CARD_SPACING == 1


def test_a_task_with_no_description_or_inputs_is_only_its_name(gui_context):
    window = queued_window(task("a", "Hold", description="", parameters=None))

    (card,) = window.panels["main"].card_tags

    assert [t.strip() for t in texts(card)] == ["[0]", "Hold"]


def test_the_cards_are_made_again_when_the_queue_changes(gui_context):
    window = queued_window(task("a"), task("b"))
    old = list(window.panels["main"].card_tags)

    window.update({"main": {"status": "Running", "current_task": None, "queue": [task("b")]}})

    panel = window.panels["main"]
    assert len(panel.card_tags) == 1
    assert not any(dpg.does_item_exist(card) for card in old)


def test_an_empty_queue_has_no_cards(gui_context):
    window = queued_window()

    assert window.panels["main"].card_tags == []
