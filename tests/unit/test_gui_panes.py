"""The headers of the Current File and Live Data panes."""

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui.components.file_window import FileWindow
from pyacquisition.gui.components.live_data_window import LiveDataWindow


@pytest.fixture
def context():
    dpg.create_context()
    yield
    dpg.destroy_context()


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def texts(item):
    found = []
    for child in dpg.get_item_children(item, 1) or []:
        if dpg.get_item_type(child).endswith("mvText"):
            found.append(dpg.get_value(child))
        found.extend(texts(child))
    return found


def drawn(item):
    return dpg.get_item_configuration(item)["text"]


# ---------------------------------------------------------------------------
# The file pane
# ---------------------------------------------------------------------------


def test_the_file_pane_is_headed_data_file_like_live_data(context):
    window = FileWindow()

    assert window.header.title == "Data File"
    assert window.header.flat, "A plain header with a line under it, as in Live Data."
    assert window.header.title_font is None or window.header.title_size == 20


def test_the_current_file_is_a_card_showing_its_name(context):
    window = FileWindow()

    window.update_file("05.00 start.data")

    assert dpg.get_value(window.file_card.name_tag) == "Current File"
    assert dpg.get_value(window.file_card.value_tag) == "05.00 start.data"
    assert window.current_file == "05.00 start.data"


def test_before_there_is_a_file_the_card_shows_a_dash(context):
    assert dpg.get_value(FileWindow().file_card.value_tag) == "-"


def test_a_very_long_file_name_is_shortened_to_fit(context):
    window = FileWindow()

    window.update_file("05.00 " + "a really rather long name " * 4 + ".data")

    assert dpg.get_value(window.file_card.value_tag).endswith("...")


def test_the_directory_is_a_card_showing_the_path(context):
    window = FileWindow()

    window.update_directory("my_data")

    assert dpg.get_value(window.directory_card.name_tag) == "Directory"
    assert dpg.get_value(window.directory_uuid) == "my_data"
    assert window.directory == "my_data"


def test_a_long_directory_keeps_its_end_where_it_differs(context):
    window = FileWindow()

    window.update_directory("D:/" + "very/long/" * 12 + "2026-09-24")

    shown = dpg.get_value(window.directory_uuid)
    assert shown.startswith("...") and shown.endswith("2026-09-24")


def test_the_cards_and_lines_are_as_wide_as_the_header(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)

    assert window.file_card.width == window.directory_card.width == window.header.width
    assert window.next_card.width == window.header.width
    for drawlist, _ in window._rules:
        assert dpg.get_item_configuration(drawlist)["width"] == window.header.width


def test_there_is_no_input_or_button_unless_it_can_start_a_file(context):
    window = FileWindow()

    assert window.next_card is None and window._rules == []
    window.update_file("05.00 start.data")  # and it is not an error


def test_the_next_file_cards_are_in_order_with_a_line_on_each_side(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)

    children = dpg.get_item_children(window.card_tag, 1)
    order = [
        window.file_card.container,
        window.next_file_card.container,
        window.directory_card.container,
        window._rules[0][0],
        window.next_card.container,
        window.block_card.container,
        window.start_card.container,
        window._rules[1][0],
    ]
    first = children.index(order[0])
    assert [children.index(item) for item in order] == list(
        range(first, first + len(order))
    ), "The next file is under the current one, and the controls are between lines."
    assert len(window._rules) == 2
    assert window.next_card.kind == "text"
    assert window.next_card.button_tag is None, "The input has no button."
    assert dpg.get_item_label(window.start_card.button_tag) == "Next File"


def test_the_current_and_next_file_are_in_normal_sized_text(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)

    for card in (window.file_card, window.next_file_card):
        assert card.font is None, "The small font, like the labels."


def test_the_input_starts_with_the_title_of_the_current_file(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)

    window.update_file("05.02 cold sweep.data")

    assert dpg.get_value(window.next_card.input_tag) == "cold sweep"


def test_what_is_typed_is_not_replaced_by_the_next_refresh(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)
    window.update_file("05.02 cold.data")
    card = window.next_card
    dpg.set_value(card.input_tag, "warm")
    dpg.get_item_callback(card.input_tag)(card.input_tag, "warm", None)

    window.update_file("05.02 cold.data")  # the poll, a second later

    assert dpg.get_value(card.input_tag) == "warm"


def press_start(window):
    """Press the button of the card that is only a button, as a click would."""
    button = window.start_card.button_tag
    dpg.get_item_callback(button)(button, None, None)


def type_title(window, text):
    card = window.next_card
    dpg.set_value(card.input_tag, text)
    dpg.get_item_callback(card.input_tag)(card.input_tag, text, None)


def tick_block(window, ticked=True):
    box = window.block_card.checkbox_tag
    dpg.set_value(box, ticked)
    dpg.get_item_callback(box)(box, ticked, None)


def test_the_name_the_next_file_would_get_is_in_a_card_and_follows_what_is_typed(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)
    window.update_file("05.02 cold.data")
    assert dpg.get_value(window.next_file_card.name_tag) == "Next File"
    assert dpg.get_value(window.next_file_card.value_tag) == "05.03 cold.data"

    type_title(window, "warm")

    assert dpg.get_value(window.next_file_card.value_tag) == "05.03 warm.data"


def test_there_is_no_preview_under_the_label_of_the_input(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)
    window.update_file("05.02 cold.data")

    assert window.next_card.caption == ""
    assert dpg.get_item_configuration(window.next_card.caption_tag)["show"] is False


def test_an_empty_name_shows_a_dash_for_the_next_file(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)
    window.update_file("05.02 cold.data")

    type_title(window, "  ")

    assert dpg.get_value(window.next_file_card.value_tag) == "-"


def test_the_button_starts_the_next_file_with_the_typed_title(context):
    started = []
    window = FileWindow(
        on_next_file=lambda title, next_block: started.append((title, next_block))
    )
    window.update_file("05.02 cold.data")

    dpg.set_value(window.next_card.input_tag, "warm")
    press_start(window)

    assert started == [("warm", False)]


def test_nothing_is_started_without_a_title(context):
    started = []
    window = FileWindow(
        on_next_file=lambda title, next_block: started.append((title, next_block))
    )
    window.update_file("05.02 cold.data")

    type_title(window, "   ")
    press_start(window)

    assert started == []


def test_the_button_card_is_only_a_button(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)
    children = dpg.get_item_children(window.start_card.container, 1)

    types = [dpg.get_item_type(child).split("::")[-1] for child in children]
    assert "mvButton" in types
    assert not any(t in ("mvInputText", "mvCheckbox", "mvInputFloat") for t in types)


def test_the_checkbox_starts_a_new_block_and_the_preview_shows_it(context):
    started = []
    window = FileWindow(
        on_next_file=lambda title, next_block: started.append((title, next_block))
    )
    window.update_file("05.02 cold.data")
    assert window.block_card.label == "Increment Block"
    assert window.block_card.value is False

    tick_block(window)
    assert dpg.get_value(window.next_file_card.value_tag) == "06.00 cold.data"

    press_start(window)
    assert started == [("cold", True)]


def test_the_box_is_unticked_after_a_new_block_is_started(context):
    window = FileWindow(on_next_file=lambda title, next_block: None)
    window.update_file("05.02 cold.data")
    tick_block(window)

    press_start(window)

    assert window.block_card.value is False
    assert dpg.get_value(window.next_file_card.value_tag) == "05.03 cold.data"


@pytest.mark.parametrize(
    "current, title, expected",
    [
        ("05.02 cold.data", "warm", "05.03 warm.data"),
        ("00.00 start.data", "a b", "00.01 a b.data"),
        ("00.09 x.data", "y", "00.10 y.data"),
        ("12.99 x.csv", "y", "12.100 y.csv"),
        ("05.02 no extension", "y", "05.03 y"),
        ("", "y", "y"),
        ("not a scribe name", "y", "y"),
    ],
)
def test_the_next_file_name(current, title, expected):
    from pyacquisition.gui.components.file_window import next_file_name

    assert next_file_name(current, title) == expected


@pytest.mark.parametrize(
    "current, title, expected",
    [
        ("05.02 cold.data", "warm", "06.00 warm.data"),
        ("00.00 start.data", "a", "01.00 a.data"),
        ("09.07 x.data", "y", "10.00 y.data"),
        ("05.02 no extension", "y", "06.00 y"),
        ("", "y", "y"),
    ],
)
def test_the_next_block_starts_at_step_zero(current, title, expected):
    from pyacquisition.gui.components.file_window import next_file_name

    assert next_file_name(current, title, next_block=True) == expected


def test_the_gui_starts_the_next_file_and_shows_the_new_one(context):
    from pyacquisition.gui import Gui

    gui = Gui()
    gui.file_window = FileWindow(on_next_file=gui._next_file)
    requests = []

    def get(endpoint, params=None, **kwargs):
        requests.append((endpoint, params))
        return {"status": 200, "data": "05.03 warm.data"}

    gui.api_client.get = get
    gui.file_window.update_file("05.02 cold.data")

    dpg.set_value(gui.file_window.next_card.input_tag, "warm")
    press_start(gui.file_window)

    assert requests == [
        ("/scribe/next_file", {"title": "warm", "next_block": False}),
        ("/scribe/current_file", None),
    ]
    assert dpg.get_value(gui.file_window.file_card.value_tag) == "05.03 warm.data"


def test_the_live_data_pane_starts_under_the_file_pane(context):
    from pyacquisition.gui.constants import FILE_PANE_HEIGHT, TOP_Y

    window = LiveDataWindow(clock=FakeClock())

    assert dpg.get_item_pos(window.window_tag)[1] >= TOP_Y + FILE_PANE_HEIGHT


def test_the_file_pane_has_no_title_bar_of_its_own(context):
    window = FileWindow()

    assert dpg.get_item_configuration(window.window_tag)["no_title_bar"] is True
    assert dpg.get_item_children(window.frame_tag, 1)[0] == window.header.container


# ---------------------------------------------------------------------------
# The live data pane
# ---------------------------------------------------------------------------


def make(clock=None):
    return LiveDataWindow(clock=clock or FakeClock())


def test_the_live_data_header_says_it_is_waiting_before_any_data(context):
    window = make()

    header = window.header
    assert (header.title, header.badge, header.style) == (
        "Live Data",
        "WAITING",
        "idle",
    )


def test_it_is_live_once_data_arrives_and_there_is_no_pill_for_it(context):
    window = make()

    window.update({"time": 1.0})

    assert window.feed == "live"
    assert window.header.badge is None, "Nothing is wrong, so no pill is needed."
    assert window.header.style == "idle"


def test_it_goes_stale_when_data_stops_arriving(context):
    clock = FakeClock()
    window = make(clock)
    window.update({"time": 1.0})

    clock.now += window.STALE_AFTER - 0.1
    window.tick()
    assert window.feed == "live", "Not yet."

    clock.now += 0.2
    window.tick()
    assert (window.header.badge, window.header.style) == ("STALE", "paused")


def test_it_is_live_again_when_data_resumes(context):
    clock = FakeClock()
    window = make(clock)
    window.update({"time": 1.0})
    clock.now += 10
    window.tick()
    assert window.header.badge == "STALE"

    window.update({"time": 2.0})

    assert window.feed == "live"
    assert window.header.badge is None


def test_ticking_before_any_data_leaves_it_waiting(context):
    clock = FakeClock()
    window = make(clock)

    clock.now += 100
    window.tick()

    assert window.header.badge == "WAITING", "There is nothing to have gone stale."


def test_the_header_is_only_redrawn_when_the_feed_changes(context):
    clock = FakeClock()
    window = make(clock)
    window.update({"time": 1.0})
    calls = []
    real_update = window.header.update
    window.header.update = lambda *a, **k: (calls.append(1), real_update(*a, **k))

    for _ in range(50):  # a frame at a time, with nothing new
        window.tick()
    window.update({"time": 2.0})

    assert calls == [], "Nothing changed, so nothing should be redrawn."


def test_the_stale_time_is_a_few_seconds(context):
    """Rows arrive several times a second, so a few seconds is a real gap."""
    assert 1.0 <= LiveDataWindow.STALE_AFTER <= 10.0


def test_each_measurement_gets_a_row_under_the_header(context):
    window = make()

    window.update({"time": 1.5, "random": 0.25})

    assert {"time", "random"} <= {t.strip() for t in texts(window.window_tag)}
    frame = dpg.get_item_children(window.window_tag, 1)[0]
    assert frame == window.frame_tag
    first = dpg.get_item_children(frame, 1)[0]
    assert first == window.header.container, "The header stays at the top."


def test_the_rows_come_before_the_loop_time(context):
    window = make()

    window.update({"time": 1.5})
    window.update({"time": 2.5, "random": 0.25})  # a row added later

    *_, above, last, rule = dpg.get_item_children(window.card_tag, 1)
    assert last == window.time_group_tag
    assert above == window._rules[-2][0], "A line is above it."
    assert rule == window._rules[-1][0], "Only the closing line is after it."


# --- the header and the values ---


def test_the_header_and_the_values_are_in_one_frame_with_no_border(context):
    window = make()
    window.update({"time": 1.5, "random": 0.25})

    assert dpg.get_item_children(window.window_tag, 1) == [window.frame_tag]
    children = dpg.get_item_children(window.frame_tag, 1)
    assert children[0] == window.header.container
    assert window.card_tag in children
    assert {"time", "random"} <= {t.strip() for t in texts(window.card_tag)}
    assert dpg.get_item_configuration(window.frame_tag)["border"] is False
    component = dpg.get_item_children(window._frame_theme, 1)[0]
    (background,) = dpg.get_item_children(component, 1)
    assert dpg.get_value(background)[3] == 0, "The frame has no background."


def test_the_frame_fits_its_contents(context):
    window = make()
    assert dpg.get_item_configuration(window.frame_tag)["auto_resize_y"] is True
    assert dpg.get_item_configuration(window.card_tag)["auto_resize_y"] is True


def test_the_header_is_flat_with_an_underline_and_no_tint(context):
    window = make()
    for feed in ("waiting", "live", "stale"):
        window.feed = None
        window._show_feed(feed)
        assert dpg.get_item_configuration(window.header._background)["fill"][3] == 0
        assert dpg.get_item_configuration(window.header._rule)["show"] is True


def test_the_underline_is_one_pixel_and_as_wide_as_the_cards(context):
    window = make()
    window.update({"a": 1.0})

    p1 = dpg.get_item_configuration(window.header._rule)["p1"]
    p2 = dpg.get_item_configuration(window.header._rule)["p2"]
    assert p1[1] == p2[1], "It is level."
    assert p2[0] - p1[0] == window.cards["a"].width == window.header.width


def test_the_header_is_tinted_in_the_other_panes_and_not_in_this_one(context):
    """Only a header made `flat` gives up its tint. The data file pane keeps its own."""
    assert make().header.flat is True


def test_the_header_is_grey_before_any_data_and_while_it_arrives(context):
    window = make()
    assert window.header.style == "idle"

    window.update({"time": 1.0})

    assert window.header.style == "idle"


def test_the_header_turns_amber_when_the_data_goes_stale_and_grey_again(context):
    clock = FakeClock()
    window = make(clock)
    window.update({"time": 1.0})

    clock.now += 10
    window.tick()
    assert window.header.style == "paused" and window.header.badge == "STALE"

    window.update({"time": 2.0})
    assert window.header.style == "idle" and window.header.badge is None


def test_a_row_shows_the_latest_value(context):
    window = make()

    window.update({"time": 1.5})
    window.update({"time": 2.5})

    assert "2.5" in [t.strip() for t in texts(window.window_tag)]
    assert "1.5" not in [t.strip() for t in texts(window.window_tag)]


def test_the_loop_time_is_shown_from_the_second_row(context):
    window = make()
    assert dpg.get_value(window.time_tag) == "0.000 s"

    window.update({"time": 1.0})
    window.update({"time": 2.0})

    assert dpg.get_value(window.time_tag).endswith(" s")


def test_the_live_data_pane_has_no_title_bar_of_its_own(context):
    window = make()
    assert dpg.get_item_configuration(window.window_tag)["no_title_bar"] is True


def test_the_header_makes_room_for_a_scroll_bar(context, monkeypatch):
    window = make()
    full = window.header.width

    monkeypatch.setattr(dpg, "get_y_scroll_max", lambda item: 400)
    window.update({"time": 1.0})

    assert window.header.width == full - 14


def test_the_loop_time_card_is_two_thirds_of_a_measurement_card_with_a_rule_under_it(
    context,
):
    window = make()
    window.update({"time": 1.0})

    ratio = window.time_card.height / window.cards["time"].height
    assert abs(ratio - 2 / 3) < 0.03
    assert len(window._rules) == 2
    for drawlist, _ in window._rules:
        assert dpg.get_item_configuration(drawlist)["height"] == 1
        assert dpg.get_item_configuration(drawlist)["width"] == window.header.width


def test_the_closing_rule_is_the_colour_of_the_header_rule(context):
    clock = FakeClock()
    window = make(clock)
    window.update({"time": 1.0})
    grey = dpg.get_item_configuration(window._rules[0][1])["color"]

    clock.now += 10
    window.tick()

    for _, line in window._rules:
        assert dpg.get_item_configuration(line)["color"] != grey
        assert dpg.get_item_configuration(line)["color"] == (
            dpg.get_item_configuration(window.header._rule)["color"]
        )


# --- pausing ---


def test_the_header_has_no_icon_unless_it_can_pause(context):
    assert make().header.on_action is None
    window = LiveDataWindow(clock=FakeClock(), on_toggle=lambda paused: None)
    assert window.header.on_action


def test_pausing_turns_the_header_and_its_lines_amber_and_shows_play(context):
    window = LiveDataWindow(clock=FakeClock(), on_toggle=lambda paused: None)
    window.update({"a": 1.0})
    assert window.header.action == "pause"

    window.set_paused(True)

    assert window.header.action == "play"
    assert (window.header.style, window.header.badge) == ("paused", "PAUSED")
    amber = dpg.get_item_configuration(window.header._rule)["color"]
    for _, line in window._rules:
        assert dpg.get_item_configuration(line)["color"] == amber

    window.set_paused(False)
    assert window.header.action == "pause" and window.header.style == "idle"


def test_a_paused_pane_does_not_go_stale_and_is_muted(context):
    from pyacquisition.gui.components.measurement_card import muted

    clock = FakeClock()
    window = LiveDataWindow(clock=clock, on_toggle=lambda paused: None)
    window.update({"a": 1.0})
    own = tuple(window.colors["a"])

    window.set_paused(True)
    clock.now += 10
    window.tick()

    assert window.header.badge == "PAUSED", "Not STALE: it was told it is paused."
    card = window.cards["a"]
    assert card.muted
    shown = dpg.get_item_configuration(card.value_tag)["color"]
    assert tuple(round(c * 255) if max(shown) <= 1 else c for c in shown[:3]) == muted(own)

    window.set_paused(False)
    assert not card.muted


def test_a_measurement_that_arrives_while_paused_is_muted(context):
    window = LiveDataWindow(clock=FakeClock(), on_toggle=lambda paused: None)
    window.set_paused(True)

    window.update({"a": 1.0})

    assert window.cards["a"].muted
    assert window.header.style == "paused"


def test_clicking_the_icon_asks_to_toggle(context, monkeypatch):
    asked = []
    window = LiveDataWindow(clock=FakeClock(), on_toggle=asked.append)

    monkeypatch.setattr(dpg, "get_drawing_mouse_pos", lambda: (window.header.width - 15, 10))
    window.header._clicked()
    window.set_paused(True)
    window.header._clicked()
    monkeypatch.setattr(dpg, "get_drawing_mouse_pos", lambda: (20, 10))
    window.header._clicked()

    assert asked == [False, True], "Told whether it is paused now. Not on the title."


def test_the_name_of_a_card_is_above_where_it_comes_from(context):
    window = LiveDataWindow(clock=FakeClock(), sources={"a": "cryo.get_temperature"})
    window.update({"a": 1.0, "b": 2.0})

    with_source, without = window.cards["a"], window.cards["b"]
    name_y = dpg.get_item_pos(with_source.name_tag)[1]
    source_y = dpg.get_item_pos(with_source.source_tag)[1]
    assert name_y < source_y, "The white name is above the grey source."
    # The ink of the pixel font is INK_DROP lower than its box, so the box is placed
    # higher, for the two lines and for one, so that they look to be in the middle.
    from pyacquisition.gui.components.measurement_card import INK_DROP

    assert abs((name_y + source_y + 13) / 2 + INK_DROP - with_source.height / 2) <= 1.5
    single = dpg.get_item_pos(without.name_tag)[1]
    assert abs(single + 13 / 2 + INK_DROP - without.height / 2) <= 1.5


def test_a_line_separates_the_last_measurement_from_the_period_card(context):
    window = LiveDataWindow(clock=FakeClock(), on_period=lambda seconds: None)
    window.update({"a": 1.0})

    children = dpg.get_item_children(window.card_tag, 1)
    first_rule = window._rules[0][0]
    assert len(window._rules) == 3
    assert children.index(window.cards_tag) + 1 == children.index(first_rule)
    assert children.index(first_rule) + 1 == children.index(window.period_card.container)
    assert children.index(window.period_card.container) + 1 == children.index(window._rules[1][0])


# --- the loop time is an average ---


class Now:
    """The time of a row, which a test sets."""

    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        return self.value


@pytest.fixture
def rows(monkeypatch):
    import types

    from pyacquisition.gui.components import live_data_window as module

    now = Now()
    monkeypatch.setattr(module, "time", types.SimpleNamespace(time=now, monotonic=now))
    return now


def send(window, now, gap):
    now.value += gap
    window.update({"x": 1.0})


def test_the_loop_time_is_the_average_of_the_latest_five(context, rows):
    window = make()
    send(window, rows, 0)  # the first row has no loop before it
    for gap in (1.0, 1.0, 1.0, 1.0, 1.0):
        send(window, rows, gap)
    assert dpg.get_value(window.time_tag) == "1.000 s"

    send(window, rows, 4.0)  # the oldest of the five drops out: 1, 1, 1, 1, 4
    assert dpg.get_value(window.time_tag) == "1.600 s"

    send(window, rows, 4.0)  # 1, 1, 1, 4, 4
    assert dpg.get_value(window.time_tag) == "2.200 s"


def test_fewer_than_five_loops_are_averaged_as_they_are(context, rows):
    window = make()
    send(window, rows, 0)
    send(window, rows, 1.0)
    send(window, rows, 3.0)

    assert dpg.get_value(window.time_tag) == "2.000 s"


def test_a_spike_is_smoothed(context, rows):
    window = make()
    send(window, rows, 0)
    for _ in range(5):
        send(window, rows, 0.5)
    send(window, rows, 2.5)

    assert dpg.get_value(window.time_tag) == "0.900 s", "Not 2.5."


def test_the_time_paused_is_not_counted_as_a_loop(context, rows):
    window = LiveDataWindow(clock=FakeClock(), on_toggle=lambda paused: None)
    send(window, rows, 0)
    send(window, rows, 0.5)
    send(window, rows, 0.5)

    window.set_paused(True)
    window.set_paused(False)
    send(window, rows, 60.0)  # the first row after a minute of nothing
    send(window, rows, 0.5)

    assert dpg.get_value(window.time_tag) == "0.500 s"


def test_the_period_card_is_the_colour_of_the_loop_time_card(context):
    window = LiveDataWindow(on_period=lambda seconds: None)

    def fill(card):
        theme = dpg.get_item_theme(card.container)
        for component in dpg.get_item_children(theme, 1):
            for item in dpg.get_item_children(component, 1):
                if dpg.get_item_configuration(item)["target"] == dpg.mvThemeCol_ChildBg:
                    return tuple(dpg.get_value(item)[:3])

    from pyacquisition.gui.components.live_data_window import TIME_BACKGROUND

    assert fill(window.period_card) == TIME_BACKGROUND
