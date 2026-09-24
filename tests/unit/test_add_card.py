"""The blank card with a + that adds a task, and the list of tasks it shows."""

from types import SimpleNamespace

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui import Gui
from pyacquisition.gui.components.add_card import (
    BACKGROUND,
    HOVERED_BACKGROUND,
    AddCard,
)
from pyacquisition.gui.components.task_manager_window import TaskManagerWindow

IDLE = {"status": "Running", "current_task": None, "queue": []}
TASK = {"id": "a", "name": "Hold", "description": "", "parameters": {}}


@pytest.fixture
def context():
    dpg.create_context()
    dpg.create_viewport(width=1000, height=900)
    with dpg.window() as window:
        yield window
    dpg.destroy_context()


def endpoint(summary):
    return SimpleNamespace(path=f"/tasks/{summary.lower()}", get=SimpleNamespace(summary=summary))


TASKS = [endpoint("NewFile"), endpoint("WaitFor"), endpoint("Hold")]


def make(names=("main",), added=None):
    added = [] if added is None else added
    window = TaskManagerWindow(
        list(names),
        tasks={name: TASKS for name in names},
        on_add=lambda manager, path: added.append((manager, path.get.summary)),
    )
    return window, added


# --- the card ---


def test_it_is_a_single_drawing_so_that_the_whole_card_is_the_button(context):
    card = AddCard(context, 300)

    assert dpg.get_item_type(card.drawlist).endswith("mvDrawlist")
    assert dpg.get_item_configuration(card.drawlist)["width"] == 300


def test_a_dark_cross_is_inside_a_white_circle_in_the_middle(context):
    card = AddCard(context, 300, height=40)

    horizontal, vertical = card._arms
    h = dpg.get_item_configuration(horizontal)
    v = dpg.get_item_configuration(vertical)
    assert h["p1"][1] == h["p2"][1] == 20 and (h["p1"][0] + h["p2"][0]) / 2 == 150
    assert v["p1"][0] == v["p2"][0] == 150 and (v["p1"][1] + v["p2"][1]) / 2 == 20
    circle = dpg.get_item_configuration(card._circle)
    assert tuple(circle["center"]) == (150, 20)
    assert circle["radius"] > 5
    scale = 255 if max(circle["fill"]) <= 1 else 1
    assert min(circle["fill"][:3]) * scale > 250, "White."
    arm = dpg.get_item_configuration(horizontal)["color"]
    assert max(arm[:3]) * (255 if max(arm) <= 1 else 1) < 60, "Dark."
    assert h["p2"][0] - h["p1"][0] < 2 * circle["radius"], "The cross is inside the circle."


def test_clicking_it_calls_back_with_no_arguments(context):
    clicks = []
    card = AddCard(context, 300, on_click=lambda: clicks.append("clicked"))

    card._clicked(None, None, None)

    assert clicks == ["clicked"]


def test_it_lights_up_under_the_mouse_and_goes_back(context, monkeypatch):
    card = AddCard(context, 300)
    hovered = {"now": False}
    monkeypatch.setattr(dpg, "is_item_hovered", lambda item: hovered["now"])

    hovered["now"] = True
    card.tick()
    lit = dpg.get_item_configuration(card._background)["fill"]
    lit_circle = dpg.get_item_configuration(card._circle)["fill"][3]
    hovered["now"] = False
    card.tick()
    dim = dpg.get_item_configuration(card._background)["fill"]

    dim_circle = dpg.get_item_configuration(card._circle)["fill"][3]
    assert tuple(lit[:3]) != tuple(dim[:3])
    assert lit_circle > dim_circle, "The circle is brighter under the mouse."
    scale = 255 if max(dim) <= 1 else 1
    assert tuple(round(x * scale) for x in dim[:3]) == BACKGROUND
    assert HOVERED_BACKGROUND != BACKGROUND


def test_it_follows_a_resize(context):
    card = AddCard(context, 300)

    card.resize(200)

    assert dpg.get_item_configuration(card.drawlist)["width"] == 200
    h = dpg.get_item_configuration(card._arms[0])
    assert (h["p1"][0] + h["p2"][0]) / 2 == 100
    assert dpg.get_item_configuration(card._circle)["center"][0] == 100


# --- at the bottom of a queue ---


def test_the_card_is_at_the_bottom_of_the_queue_under_the_queued_tasks(context):
    window, _ = make()
    window.update({"main": {**IDLE, "queue": [TASK]}})
    panel = window.panels["main"]

    children = dpg.get_item_children(panel.section_tag, 1)
    assert children.index(panel.queue_tag) + 1 == children.index(panel.add_card.drawlist)
    assert children[-1] == panel.add_card.drawlist


def test_the_queue_is_rebuilt_in_front_of_the_card_not_after_it(context):
    window, _ = make()
    panel = window.panels["main"]

    for queue in ([], [TASK], [TASK, {**TASK, "id": "b"}], []):
        window.update({"main": {**IDLE, "queue": queue}})
        children = dpg.get_item_children(panel.section_tag, 1)
        assert children.index(panel.queue_tag) < children.index(panel.add_card.drawlist)


def test_with_several_managers_the_gap_is_under_the_card(context):
    window, _ = make(("main", "control"))
    window.update({"main": {**IDLE, "queue": [TASK]}, "control": IDLE})
    panel = window.panels["main"]

    children = dpg.get_item_children(panel.section_tag, 1)
    assert children[-2:] == [panel.add_card.drawlist, panel.gap_tag]
    assert children.index(panel.queue_tag) < children.index(panel.add_card.drawlist)


def test_every_manager_has_its_own_card(context):
    window, _ = make(("main", "control"))

    assert all(panel.add_card for panel in window.panels.values())


def test_there_is_no_card_without_tasks_to_add_or_a_way_to_add_them(context):
    assert TaskManagerWindow(["main"]).panels["main"].add_card is None
    assert TaskManagerWindow(["main"], tasks={"main": TASKS}).panels["main"].add_card is None
    assert (
        TaskManagerWindow(["main"], tasks={"main": []}, on_add=lambda *a: None)
        .panels["main"]
        .add_card
        is None
    )


def test_it_is_as_wide_as_the_header(context):
    window, _ = make()
    panel = window.panels["main"]

    panel.header.resize(300)
    panel.fit_add_card()

    assert panel.add_card.width == 300


def test_it_lights_up_through_the_window_tick(context, monkeypatch):
    window, _ = make()
    panel = window.panels["main"]
    monkeypatch.setattr(dpg, "is_item_hovered", lambda item: item == panel.add_card.drawlist)

    window.tick()

    assert panel.add_card.hovered


# --- the list of tasks ---


def test_the_list_is_made_when_the_card_is_first_clicked(context):
    window, _ = make()
    panel = window.panels["main"]
    assert panel.add_menu_tag is None

    panel.add_card._clicked()

    assert dpg.does_item_exist(panel.add_menu_tag)
    assert dpg.get_item_configuration(panel.add_menu_tag)["show"] is True
    assert dpg.get_item_configuration(panel.add_menu_tag)["popup"] is True


def test_the_list_offers_each_task_by_its_summary(context):
    window, _ = make()
    panel = window.panels["main"]

    panel.add_card._clicked()

    labels = [dpg.get_item_label(item).strip() for item in panel.add_items.values()]
    assert labels == ["NewFile", "WaitFor", "Hold"]


def test_picking_a_task_closes_the_list_and_adds_it(context):
    window, added = make(("main", "control"))
    panel = window.panels["control"]
    panel.add_card._clicked()

    item = panel.add_items["/tasks/waitfor"]
    dpg.set_value(item, True)
    dpg.get_item_callback(item)(item, True, dpg.get_item_user_data(item))

    assert added == [("control", "WaitFor")]
    assert dpg.get_item_configuration(panel.add_menu_tag)["show"] is False
    assert dpg.get_value(item) is False, "It is not a choice that stays selected."


def test_the_list_is_shown_again_by_the_next_click(context):
    window, _ = make()
    panel = window.panels["main"]
    panel.add_card._clicked()
    menu = panel.add_menu_tag
    dpg.configure_item(menu, show=False)

    panel.add_card._clicked()

    assert panel.add_menu_tag == menu, "The same list, not another."
    assert dpg.get_item_configuration(menu)["show"] is True


# --- in the Gui ---


def test_the_gui_lists_the_task_endpoints_of_every_manager():
    from pyacquisition.gui.managers import task_paths

    class Schema:
        paths = {}

    assert Gui._addable_tasks(None, ["main"]) == {}
    assert set(Gui._addable_tasks(Schema(), ["main", "control"])) == {"main", "control"}


def test_a_picked_task_opens_the_window_that_asks_for_its_inputs(context, monkeypatch):
    gui = Gui()
    gui.task_window = TaskManagerWindow(["main", "control"])
    opened = []
    gui._draw_popup = lambda sender, data, user_data: opened.append(user_data)
    path = endpoint("Hold")

    gui._add_task("control", path)

    assert opened == [{"path": path, "manager": "control"}]


def test_with_one_manager_the_window_does_not_name_it(context):
    gui = Gui()
    gui.task_window = TaskManagerWindow(["main"])
    opened = []
    gui._draw_popup = lambda sender, data, user_data: opened.append(user_data)

    gui._add_task("main", endpoint("Hold"))

    assert opened[0]["manager"] is None
