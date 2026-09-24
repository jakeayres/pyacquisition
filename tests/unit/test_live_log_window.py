"""The log pane, and the generic card that chooses one of a few options."""

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui.components import live_log_window as module
from pyacquisition.gui.components.choice_card import ChoiceCard
from pyacquisition.gui.constants import page_width
from pyacquisition.gui.components.live_log_window import (
    LEVELS,
    MAX_LOGS,
    LiveLogWindow,
    rank,
)


@pytest.fixture
def context():
    dpg.create_context()
    dpg.create_viewport(width=1200, height=800)
    yield
    dpg.destroy_context()


def log(level="info", message="hello", time=1_800_000_000.0):
    return {"time": time, "level": level, "message": message}


def lines(window):
    """The text of each line that is shown: its time and tag, and its message."""
    rows = dpg.get_item_children(window.table_tag, 1)
    return [
        [dpg.get_value(t) for t in dpg.get_item_children(cell_row, 1)]
        for cell_row in rows
    ]


def messages(window):
    return [
        dpg.get_value(dpg.get_item_children(row, 1)[1])
        for row in dpg.get_item_children(window.table_tag, 1)
    ]


# --- the look ---


def test_it_is_headed_log_like_the_other_panes(context):
    window = LiveLogWindow()

    assert window.header.title == "Log"
    assert window.header.flat, "A plain header with a line under it."
    assert dpg.get_item_configuration(window.window_tag)["no_title_bar"] is True


def test_the_level_is_chosen_in_a_card_under_the_header(context):
    window = LiveLogWindow()

    children = dpg.get_item_children(window.frame_tag, 1)
    assert children[:2] == [window.header.container, window.level_card.container]
    assert window.level_card.options == list(LEVELS)


def test_it_fills_the_left_part_of_the_window_and_is_as_tall_as_it(context, monkeypatch):
    from pyacquisition.gui.constants import PANE_X, page_width

    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1920)
    window = LiveLogWindow()

    window.update_layout()

    assert dpg.get_item_pos(window.window_tag) == [PANE_X, 20]
    width = dpg.get_item_configuration(window.window_tag)["width"]
    assert width == page_width(1920)
    assert PANE_X + width <= 1920 * 5 // 12, "It stays clear of the plot."
    assert dpg.get_item_configuration(window.window_tag)["height"] > 600


def test_the_header_and_the_level_card_follow_its_width(context, monkeypatch):
    window = LiveLogWindow()
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1920)

    window.update_layout()

    assert window.header.width == window.level_card.width == window.width - 16
    assert window.width == page_width(1920)


def test_the_messages_are_drawn_again_when_the_width_changes(context, monkeypatch):
    window = LiveLogWindow()
    window.add_log(log("info", "word " * 80))
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 3200)
    before = messages(window)[0]

    window.update_layout()

    assert len(messages(window)[0]) > len(before), "More of it fits in a wider window."


def test_the_lines_are_packed_as_close_as_their_text_is_tall(context):
    """The padding of a frame would add six pixels to every line of a table."""
    window = LiveLogWindow()
    component = dpg.get_item_children(window._log_theme, 1)[0]
    styles = {
        dpg.get_item_configuration(i)["target"]: list(dpg.get_value(i))
        for i in dpg.get_item_children(component, 1)
        if dpg.get_item_type(i).endswith("mvThemeStyle")
    }

    assert styles[dpg.mvStyleVar_CellPadding][1] == 0
    assert styles[dpg.mvStyleVar_FramePadding][:2] == [0, 0]
    assert styles[dpg.mvStyleVar_ItemSpacing][:2] == [0, 0]
    assert window._log_theme == dpg.get_item_theme(window.table_tag)


def test_a_line_has_a_time_a_level_tag_and_a_message(context):
    window = LiveLogWindow()

    window.add_log(log("warning", "too slow"))

    ((prefix, message),) = lines(window)
    assert prefix.endswith(" WRN") and len(prefix) == len("12:03:44 WRN")
    assert prefix[2] == prefix[5] == ":"
    assert message == "too slow"


def test_each_level_has_its_own_colour_for_its_tag(context):
    window = LiveLogWindow(level="debug")
    for level in ("debug", "info", "warning", "error"):
        window.add_log(log(level))

    colours = []
    for row in dpg.get_item_children(window.table_tag, 1):
        tag = dpg.get_item_children(row, 1)[0]
        colours.append(tuple(dpg.get_item_configuration(tag)["color"][:3]))

    assert len(set(colours)) == 4


def test_a_message_is_one_line_however_it_was_written(context):
    window = LiveLogWindow()

    window.add_log(log("info", "first\nsecond   line"))

    assert messages(window) == ["first second line"]


def test_a_message_that_is_too_long_is_cut_short_and_shown_in_full_on_hover(context):
    window = LiveLogWindow()
    long = "word " * 80

    window.add_log(log("info", long))

    (shown,) = messages(window)
    assert shown.endswith("...") and len(shown) < len(long)
    assert any(dpg.get_item_type(i).endswith("mvTooltip") for i in dpg.get_all_items())

def test_a_short_message_has_no_tooltip(context):
    window = LiveLogWindow()

    window.add_log(log("info", "short"))

    assert not any(dpg.get_item_type(i).endswith("mvTooltip") for i in dpg.get_all_items())


# --- the level ---


def test_it_starts_at_info_so_that_debug_does_not_fill_it(context):
    window = LiveLogWindow()
    assert window.level == "info" and window.level_card.value == "info"

    window.add_log(log("debug", "noise"))
    window.add_log(log("info", "news"))

    assert messages(window) == ["news"]


@pytest.mark.parametrize(
    "level, shown",
    [
        ("debug", ["debug", "info", "warning", "error"]),
        ("info", ["info", "warning", "error"]),
        ("warning", ["warning", "error"]),
        ("error", ["error"]),
    ],
)
def test_a_level_shows_itself_and_everything_worse(context, level, shown):
    window = LiveLogWindow(level=level)

    for name in ("trace", "debug", "info", "warning", "error"):
        window.add_log(log(name, name))

    assert messages(window) == shown, "Trace is below every level that can be chosen."


def test_an_exception_is_as_bad_as_an_error_and_an_unknown_level_is_an_info(context):
    window = LiveLogWindow(level="error")
    window.add_log(log("exception", "boom"))
    window.add_log(log("mystery", "who knows"))

    assert messages(window) == ["boom"]
    assert rank("mystery") == rank("info")
    assert rank("exception") == rank("error") > rank("warning") > rank("info")


def test_choosing_a_lower_level_shows_what_was_hidden(context):
    window = LiveLogWindow()
    for name in ("debug", "info", "debug", "error"):
        window.add_log(log(name, name))
    assert messages(window) == ["info", "error"]

    window.set_level("debug")

    assert messages(window) == ["debug", "info", "debug", "error"], "In the order they came."
    assert window.level_card.value == "debug"


def test_choosing_a_higher_level_hides_them_and_a_lower_one_brings_them_back(context):
    window = LiveLogWindow(level="debug")
    for name in ("debug", "info", "warning", "error"):
        window.add_log(log(name, name))

    window.set_level("warning")
    assert messages(window) == ["warning", "error"]
    window.set_level("debug")
    assert messages(window) == ["debug", "info", "warning", "error"]


def test_clicking_a_level_in_the_card_changes_the_level(context):
    window = LiveLogWindow()
    window.add_log(log("debug", "noise"))

    button = window.level_card.option_tags["debug"]
    dpg.get_item_callback(button)(button, None, dpg.get_item_user_data(button))

    assert window.level == "debug" and messages(window) == ["noise"]


def test_an_unknown_level_is_refused(context):
    window = LiveLogWindow()
    with pytest.raises(ValueError, match="debug, info, warning, error"):
        window.set_level("chatty")
    with pytest.raises(ValueError):
        LiveLogWindow(level="chatty")


def test_the_header_says_how_many_messages_are_hidden(context):
    window = LiveLogWindow()

    assert window.header.badge is None
    window.add_log(log("debug", "a"))
    window.add_log(log("debug", "b"))
    assert window.header.badge == "2 HIDDEN"

    window.add_log(log("info", "c"))
    assert window.header.badge == "2 HIDDEN"

    window.set_level("debug")
    assert window.header.badge is None
    window.set_level("error")
    assert window.header.badge == "3 HIDDEN"


# --- keeping them ---


def test_it_keeps_only_the_latest_messages(context, monkeypatch):
    monkeypatch.setattr(module, "MAX_LOGS", 5)
    window = LiveLogWindow(level="debug")

    for i in range(9):
        window.add_log(log("info", f"m{i}"))

    assert messages(window) == ["m4", "m5", "m6", "m7", "m8"]
    assert len(window.entries) == 5


def test_a_message_that_drops_off_while_hidden_is_not_still_counted(context, monkeypatch):
    monkeypatch.setattr(module, "MAX_LOGS", 3)
    window = LiveLogWindow()

    for i in range(6):
        window.add_log(log("debug", f"d{i}"))

    assert window.hidden == 3 == len(window.entries)


def test_the_default_keeps_a_few_hundred():
    assert 100 <= MAX_LOGS <= 5000


# --- following the log ---


def test_it_follows_the_log_until_it_is_scrolled_up_to_read(context, monkeypatch):
    window = LiveLogWindow()
    scrolls = []
    monkeypatch.setattr(dpg, "set_y_scroll", lambda item, y: scrolls.append(y))
    monkeypatch.setattr(dpg, "get_y_scroll_max", lambda item: 500)

    monkeypatch.setattr(dpg, "get_y_scroll", lambda item: 100)
    window.tick()
    assert scrolls == [500], "It follows, since it was not scrolled away."

    window._stick = False
    monkeypatch.setattr(dpg, "get_y_scroll", lambda item: 100)  # scrolled up
    window.tick()
    assert scrolls == [500] and window._stick is False, "Left alone while it is read."

    monkeypatch.setattr(dpg, "get_y_scroll", lambda item: 498)  # back at the bottom
    window.tick()
    assert window._stick is True


def test_choosing_a_level_goes_back_to_following(context):
    window = LiveLogWindow()
    window._stick = False

    window.set_level("debug")

    assert window._stick is True


# --- the choice card ---


def test_a_choice_card_has_a_button_for_each_option_and_one_is_chosen(context):
    with dpg.window() as parent:
        card = ChoiceCard(parent, 400, "Level", ["a", "b", "c"], value="b")

    assert list(card.option_tags) == ["a", "b", "c"]
    assert card.value == "b"
    assert dpg.get_item_theme(card.option_tags["b"]) == card._chosen_theme
    assert dpg.get_item_theme(card.option_tags["a"]) == card._plain_theme


def test_it_takes_the_text_of_a_button_apart_from_its_value(context):
    with dpg.window() as parent:
        card = ChoiceCard(parent, 400, "Level", [("d", "Debug"), ("i", "Info")])

    assert dpg.get_item_label(card.option_tags["d"]) == "Debug"
    assert card.value == "d", "The first, if none is given."


def test_clicking_an_option_chooses_it_and_says_so(context):
    changes = []
    with dpg.window() as parent:
        card = ChoiceCard(parent, 400, "Level", ["a", "b"], on_change=changes.append)

    button = card.option_tags["b"]
    dpg.get_item_callback(button)(button, None, "b")

    assert card.value == "b" and changes == ["b"]
    assert dpg.get_item_theme(button) == card._chosen_theme
    assert dpg.get_item_theme(card.option_tags["a"]) == card._plain_theme


def test_setting_it_from_outside_does_not_say_so(context):
    changes = []
    with dpg.window() as parent:
        card = ChoiceCard(parent, 400, "Level", ["a", "b"], on_change=changes.append)

    card.set_value("b")

    assert card.value == "b" and changes == []
    with pytest.raises(ValueError):
        card.set_value("z")


def test_a_choice_needs_options_and_a_value_that_is_one_of_them(context):
    with dpg.window() as parent:
        with pytest.raises(ValueError, match="at least one"):
            ChoiceCard(parent, 400, "Level", [])
        with pytest.raises(ValueError, match="one of"):
            ChoiceCard(parent, 400, "Level", ["a"], value="z")


def test_the_options_are_in_a_row_at_the_right_edge(context):
    with dpg.window() as parent:
        card = ChoiceCard(parent, 400, "Level", ["a", "b", "c"], option_width=50)

    xs = [dpg.get_item_pos(tag)[0] for tag in card.option_tags.values()]
    assert xs == sorted(xs) and xs[1] - xs[0] > 50
    assert xs[-1] + 50 == 400 - 10, "The last is at the right edge of the card."
