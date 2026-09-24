"""The pages that the tabs of the menu show, and the Instruments page."""

from types import SimpleNamespace

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui import PAGES, Gui
from pyacquisition.gui.components.file_window import FileWindow
from pyacquisition.gui.components.instruments_window import InstrumentsWindow
from pyacquisition.gui.components.live_data_window import LiveDataWindow
from pyacquisition.gui.components.live_log_window import LiveLogWindow
from pyacquisition.gui.components.sidebar import Sidebar
from pyacquisition.gui.components.task_manager_window import TaskManagerWindow
from pyacquisition.gui.constants import PANE_X, page_width


@pytest.fixture
def context():
    dpg.create_context()
    dpg.create_viewport(width=1920, height=900)
    yield
    dpg.destroy_context()


def endpoint(uid, summary):
    return SimpleNamespace(
        path=f"/{uid}/{summary.lower()}", get=SimpleNamespace(summary=summary)
    )


# --- the pages ---


def make_gui():
    gui = Gui()
    gui.file_window = FileWindow()
    gui.live_data_window = LiveDataWindow()
    gui.task_window = TaskManagerWindow(["main"])
    gui.instruments_window = InstrumentsWindow()
    gui.live_log_window = LiveLogWindow()
    gui.pages = {
        "Experiment": [
            gui.file_window.window_tag,
            gui.live_data_window.window_tag,
        ],
        "Task Queue": [gui.task_window.window_tag],
        "Instruments": [gui.instruments_window.window_tag],
        "Logs": [gui.live_log_window.window_tag],
    }
    gui.sidebar = Sidebar(pages=PAGES, on_select=gui.show_page)
    return gui


def shown(gui):
    return {
        page: [dpg.get_item_configuration(w)["show"] for w in windows]
        for page, windows in gui.pages.items()
    }


def test_the_tabs_are_experiment_task_queue_instruments_and_logs():
    assert PAGES == ("Experiment", "Task Queue", "Instruments", "Logs")


def test_showing_a_page_hides_the_others(context):
    gui = make_gui()

    gui.show_page("Instruments")
    assert shown(gui) == {
        "Experiment": [False, False],
        "Task Queue": [False],
        "Instruments": [True],
        "Logs": [False],
    }

    gui.show_page("Experiment")
    assert shown(gui) == {
        "Experiment": [True, True],
        "Task Queue": [False],
        "Instruments": [False],
        "Logs": [False],
    }

    gui.show_page("Task Queue")
    assert shown(gui)["Task Queue"] == [True] and not any(shown(gui)["Experiment"])


def test_the_experiment_page_is_the_file_window_and_live_data(context):
    gui = make_gui()

    assert gui.pages["Experiment"] == [
        gui.file_window.window_tag,
        gui.live_data_window.window_tag,
    ]


def test_the_task_queue_is_a_page_of_its_own(context):
    gui = make_gui()

    assert gui.pages["Task Queue"] == [gui.task_window.window_tag]
    assert gui.task_window.window_tag not in gui.pages["Experiment"]


def test_clicking_a_tab_shows_its_page(context):
    gui = make_gui()
    tab = gui.sidebar.tabs["Logs"]

    dpg.get_item_callback(tab)(tab, True, "Logs")

    assert shown(gui)["Logs"] == [True] and shown(gui)["Instruments"] == [False]


def test_an_unknown_page_is_refused(context):
    gui = make_gui()
    with pytest.raises(ValueError, match="Experiment, Task Queue, Instruments, Logs"):
        gui.show_page("Settings")


def layout_all(gui):
    gui.file_window.fit()
    gui.live_data_window.tick()
    gui.task_window.tick()
    gui.instruments_window.update_layout()
    gui.live_log_window.update_layout()


def test_every_page_is_clear_of_the_plot(context, monkeypatch):
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1920)
    gui = make_gui()
    layout_all(gui)

    for window in (
        gui.file_window.window_tag,
        gui.live_data_window.window_tag,
        gui.task_window.window_tag,
        gui.instruments_window.window_tag,
        gui.live_log_window.window_tag,
    ):
        x, _ = dpg.get_item_pos(window)
        assert x == PANE_X
        assert x + dpg.get_item_configuration(window)["width"] <= 1920 * 5 // 12


def test_every_page_is_the_same_width(context, monkeypatch):
    """The Task Queue, the Instruments and the Log are as wide as each other, and so
    are the Data File and Live Data windows, which can expand to that width too."""
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1920)
    gui = make_gui()
    layout_all(gui)

    widths = {
        dpg.get_item_configuration(window)["width"]
        for window in (
            gui.file_window.window_tag,
            gui.live_data_window.window_tag,
            gui.task_window.window_tag,
            gui.instruments_window.window_tag,
            gui.live_log_window.window_tag,
        )
    }
    assert widths == {page_width(1920)}


def test_the_headers_and_cards_follow_the_wider_windows(context, monkeypatch):
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1920)
    gui = make_gui()
    layout_all(gui)
    width = page_width(1920) - 16

    assert gui.file_window.header.width == gui.file_window.file_card.width == width
    assert gui.live_data_window.header.width == width
    assert gui.live_data_window.time_card.width == width
    panel = gui.task_window.panels["main"]
    assert panel.header.width == width


def test_the_windows_widen_and_narrow_with_the_viewport(context, monkeypatch):
    gui = make_gui()
    for viewport in (1920, 2400, 1500):
        monkeypatch.setattr(dpg, "get_viewport_client_width", lambda v=viewport: v)
        layout_all(gui)
        for window in (gui.file_window.window_tag, gui.task_window.window_tag):
            assert dpg.get_item_configuration(window)["width"] == page_width(viewport)


def test_the_pages_start_beside_the_menu_and_the_right_seven_twelfths_are_left_clear(context):
    gui = make_gui()

    assert PANE_X > 253
    assert page_width(1920) == 1920 * 5 // 12 - PANE_X - 10
    assert PANE_X + page_width(1920) <= 1920 * 5 // 12, "They end where the plot starts."


def test_the_endpoints_of_an_instrument_are_the_paths_that_start_with_its_name(context):
    schema = SimpleNamespace(
        paths={
            "/furnace/get_temperature": endpoint("furnace", "Get Temperature"),
            "/furnace_pid/set_gain": endpoint("furnace_pid", "Set Gain"),
            "/rack/pause": endpoint("rack", "Pause"),
        }
    )

    found = Gui._instrument_endpoints(schema, {"furnace": "Furnace", "furnace_pid": "PID"})

    assert [p.get.summary for p in found["furnace"]] == ["Get Temperature"]
    assert [p.get.summary for p in found["furnace_pid"]] == ["Set Gain"]
    assert Gui._instrument_endpoints(None, {"furnace": "x"}) == {}


def test_picking_an_endpoint_opens_the_window_that_asks_for_its_inputs(context):
    gui = Gui()
    opened = []
    gui._draw_popup = lambda sender, data, user_data: opened.append(user_data)
    path = endpoint("furnace", "Read")

    gui._pick_instrument_endpoint("furnace", path)

    assert opened == [{"path": path, "manager": None}]


# --- the Instruments page ---


def make_instruments(picked=None):
    picked = [] if picked is None else picked
    window = InstrumentsWindow(on_pick=lambda name, path: picked.append((name, path.get.summary)))
    window.set_instruments(
        {"furnace": "Lakeshore 340", "lockin": "SR830"},
        {
            "furnace": [endpoint("furnace", "Get Temperature"), endpoint("furnace", "Set Setpoint")],
            "lockin": [endpoint("lockin", "Read")],
        },
    )
    return window, picked


def test_it_is_headed_instruments_like_the_other_panes(context):
    window, _ = make_instruments()

    assert window.header.title == "Instruments" and window.header.flat
    assert dpg.get_item_configuration(window.window_tag)["no_title_bar"] is True


def test_there_is_a_card_for_each_instrument_with_its_name_what_it_is_and_its_endpoints(context):
    window, _ = make_instruments()

    assert list(window.cards) == ["furnace", "lockin"]
    furnace = window.cards["furnace"]
    assert dpg.get_value(furnace.name_tag) == "furnace"
    assert dpg.get_value(furnace.source_tag) == "Lakeshore 340"
    assert dpg.get_value(furnace.value_tag) == "2 endpoints"
    assert dpg.get_value(window.cards["lockin"].value_tag) == "1 endpoint"


def test_the_cards_have_their_own_colours(context):
    window, _ = make_instruments()

    assert window.cards["furnace"].color != window.cards["lockin"].color


def test_the_lists_are_closed_until_the_card_is_clicked(context):
    window, _ = make_instruments()
    assert all(not dpg.get_item_configuration(g)["show"] for g in window.lists.values())

    window.toggle("furnace")

    assert dpg.get_item_configuration(window.lists["furnace"])["show"] is True
    assert dpg.get_item_configuration(window.lists["lockin"])["show"] is False


def test_clicking_the_card_again_closes_the_list(context):
    window, _ = make_instruments()

    window.toggle("furnace")
    window.toggle("furnace")

    assert dpg.get_item_configuration(window.lists["furnace"])["show"] is False


def test_several_lists_can_be_open_at_once(context):
    window, _ = make_instruments()

    window.toggle("furnace")
    window.toggle("lockin")

    assert window.open == {"furnace", "lockin"}


def test_clicking_a_card_toggles_it(context):
    window, _ = make_instruments()
    card = window.cards["furnace"]

    handlers = dpg.get_item_info(card.drawlist)["handlers"]
    (handler,) = dpg.get_item_children(handlers, 1)
    dpg.get_item_callback(handler)(handler, None)

    assert "furnace" in window.open


def test_each_list_has_a_line_for_each_endpoint(context):
    window, _ = make_instruments()

    labels = [
        dpg.get_item_label(item).strip()
        for item in dpg.get_item_children(window.lists["furnace"], 1)
    ]
    assert labels == ["Get Temperature", "Set Setpoint"]


def test_picking_an_endpoint_says_which_instrument_and_which_endpoint(context):
    window, picked = make_instruments()
    item = dpg.get_item_children(window.lists["furnace"], 1)[1]

    dpg.set_value(item, True)
    dpg.get_item_callback(item)(item, True, dpg.get_item_user_data(item))

    assert picked == [("furnace", "Set Setpoint")]
    assert dpg.get_value(item) is False, "It does something, and is not a choice."


def test_with_no_instruments_it_says_so(context):
    window = InstrumentsWindow()
    window.set_instruments({}, {})

    assert dpg.get_value(window.empty_tag) == "No instruments"
    assert window.cards == {}


def test_setting_instruments_again_replaces_the_old_ones(context):
    window, _ = make_instruments()
    window.toggle("furnace")

    window.set_instruments({"magnet": "IPS"}, {"magnet": []})

    assert list(window.cards) == ["magnet"] and window.open == set()
    assert dpg.get_value(window.cards["magnet"].value_tag) == "0 endpoints"


def test_an_instrument_with_no_endpoints_is_still_shown(context):
    window = InstrumentsWindow()
    window.set_instruments({"clock": "Clock"}, {})

    assert "clock" in window.cards
    window.toggle("clock")  # and it is not an error


def test_it_fills_the_left_part_and_the_cards_follow_its_width(context, monkeypatch):
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1920)
    window, _ = make_instruments()

    window.update_layout()

    width = dpg.get_item_configuration(window.window_tag)["width"]
    assert width == page_width(1920)
    assert dpg.get_item_pos(window.window_tag) == [PANE_X, 20]
    for card in window.cards.values():
        assert card.width == window.header.width
