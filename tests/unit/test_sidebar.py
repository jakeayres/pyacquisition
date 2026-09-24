"""The menu down the left of the window, whose tabs change the page that is shown."""

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui.components import sidebar as sidebar_module
from pyacquisition.gui.components.sidebar import DOCS_URL, TITLE, WIDTH, Sidebar
from pyacquisition.gui.constants import SIDEBAR_WIDTH

PAGES = ("Experiment", "Instruments", "Logs")


@pytest.fixture
def context():
    dpg.create_context()
    yield
    dpg.destroy_context()


def make(**options):
    shown = []
    return Sidebar(pages=PAGES, on_select=shown.append, **options), shown


def click(bar, page):
    tab = bar.tabs[page]
    dpg.get_item_callback(tab)(tab, True, page)


def test_it_fills_the_far_left_edge(context):
    bar, _ = make()

    assert dpg.get_item_configuration(bar.window_tag)["width"] == WIDTH == SIDEBAR_WIDTH
    assert dpg.get_item_pos(bar.window_tag) == [0, 0]


def test_it_fills_the_height_of_the_window_with_square_corners(context):
    bar, _ = make()
    dpg.create_viewport(width=800, height=700)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    bar.tick()

    assert dpg.get_item_configuration(bar.window_tag)["height"] == dpg.get_viewport_client_height()
    component = dpg.get_item_children(bar._theme, 1)[0]
    rounding = [
        dpg.get_value(i)
        for i in dpg.get_item_children(component, 1)
        if dpg.get_item_type(i).endswith("mvThemeStyle")
        and dpg.get_item_configuration(i)["target"] == dpg.mvStyleVar_WindowRounding
    ]
    assert rounding and rounding[0][0] == 0


def test_the_link_is_pushed_to_the_bottom_as_the_window_grows(context):
    bar, _ = make()
    dpg.create_viewport(width=800, height=900)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    bar.tick()

    assert dpg.get_item_configuration(bar.spacer_tag)["height"] > 300


def test_it_has_a_tab_for_each_page_in_order_between_the_title_and_the_link(context):
    bar, _ = make()

    children = dpg.get_item_children(bar.window_tag, 1)
    assert children[0] == bar.title_tag
    assert children[-1] == bar.link_tag
    tabs = [bar.tabs[page] for page in PAGES]
    indexes = [children.index(tab) for tab in tabs]
    assert indexes == sorted(indexes)
    assert [dpg.get_item_label(tab).strip() for tab in tabs] == list(PAGES)
    assert dpg.get_value(bar.title_tag) == TITLE == "MyDashboard"


def test_the_first_page_is_shown_to_start_with_and_its_tab_is_lit(context):
    bar, _ = make()

    assert bar.selected == "Experiment"
    assert [dpg.get_value(bar.tabs[page]) for page in PAGES] == [True, False, False]


def test_clicking_a_tab_shows_its_page_and_lights_only_that_tab(context):
    bar, shown = make()

    click(bar, "Logs")

    assert shown == ["Logs"] and bar.selected == "Logs"
    assert [dpg.get_value(bar.tabs[page]) for page in PAGES] == [False, False, True]


def test_clicking_the_tab_of_the_page_that_is_shown_leaves_it_lit(context):
    """A selectable unselects itself when it is clicked. A tab must not."""
    bar, shown = make()

    dpg.set_value(bar.tabs["Experiment"], False)  # what the click did
    click(bar, "Experiment")

    assert dpg.get_value(bar.tabs["Experiment"]) is True


def test_a_page_can_be_selected_from_outside_without_saying_so(context):
    bar, shown = make()

    bar.select("Instruments", notify=False)

    assert bar.selected == "Instruments" and shown == []
    assert dpg.get_value(bar.tabs["Instruments"]) is True


def test_an_unknown_page_is_refused(context):
    bar, _ = make()

    with pytest.raises(ValueError, match="Experiment, Instruments, Logs"):
        bar.select("Settings")


def test_it_works_with_no_pages_and_no_callback(context):
    bar = Sidebar()

    assert bar.selected is None and bar.tabs == {}


def test_the_title_can_be_named(context):
    assert dpg.get_value(Sidebar(title="Furnace").title_tag) == "Furnace"


def test_it_has_a_link_to_the_docs_at_the_bottom(context):
    bar, _ = make()

    assert dpg.get_item_label(bar.link_tag) == "Built with PyAcquisition"
    assert DOCS_URL == "https://pyacquisition.readthedocs.io"


def test_clicking_the_link_opens_the_docs_and_does_not_stay_selected(context, monkeypatch):
    bar, _ = make()
    opened = []
    monkeypatch.setattr(sidebar_module.webbrowser, "open", opened.append)

    dpg.set_value(bar.link_tag, True)
    dpg.get_item_callback(bar.link_tag)(bar.link_tag, True, DOCS_URL)

    assert opened == ["https://pyacquisition.readthedocs.io"]
    assert dpg.get_value(bar.link_tag) is False


def test_it_is_a_dark_panel_a_little_brighter_than_the_pages_with_light_text(context):
    bar, _ = make()
    component = dpg.get_item_children(bar._theme, 1)[0]
    values = {
        dpg.get_item_configuration(i)["target"]: dpg.get_value(i)
        for i in dpg.get_item_children(component, 1)
        if dpg.get_item_type(i).endswith("mvThemeColor")
    }

    background = tuple(values[dpg.mvThemeCol_WindowBg][:3])
    assert max(background) < 60, "Dark."
    assert background != (0, 0, 0), "Brighter than the black behind the pages."
    assert background[2] > background[0], "A little blue, like the cards."
    assert min(values[dpg.mvThemeCol_Text][:3]) > 200, "Light text."
    assert values[dpg.mvThemeCol_Border][3] > 0, "A thin edge, so that it reads as a menu."
