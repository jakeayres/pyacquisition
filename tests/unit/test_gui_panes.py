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


def test_the_file_pane_has_a_header_with_a_caption(context):
    window = FileWindow()

    assert window.header.caption == "DATA FILE"
    assert drawn(window.header._caption) == "DATA FILE"
    assert window.header.style == "neutral"


def test_the_file_name_is_the_title_of_the_header(context):
    window = FileWindow()

    window.update_file("05.00 start.data")

    assert window.header.title == "05.00 start.data"
    assert drawn(window.header._title) == "05.00 start.data"


def test_before_there_is_a_file_the_title_is_a_dash(context):
    assert FileWindow().header.title == "-"


def test_the_caption_stays_when_the_file_changes(context):
    window = FileWindow()

    window.update_file("05.00 start.data")
    window.update_file("05.01 sweep.data")

    assert window.header.title == "05.01 sweep.data"
    assert drawn(window.header._caption) == "DATA FILE"


def test_a_very_long_file_name_is_shortened_to_fit(context):
    window = FileWindow()

    window.update_file("05.00 " + "a really rather long name " * 4 + ".data")

    assert drawn(window.header._title).endswith("...")


def test_the_directory_is_shown_under_the_header(context):
    window = FileWindow()

    window.update_directory("my_data")

    assert dpg.get_value(window.directory_uuid) == "my_data"


def test_the_file_pane_has_no_title_bar_of_its_own(context):
    window = FileWindow()
    (item,) = [
        i
        for i in dpg.get_all_items()
        if dpg.get_item_type(i).endswith("mvWindowAppItem")
    ]
    assert dpg.get_item_configuration(item)["no_title_bar"] is True
    assert window.header.container in dpg.get_item_children(item, 1)


# ---------------------------------------------------------------------------
# The live data pane
# ---------------------------------------------------------------------------


def make(clock=None):
    return LiveDataWindow(clock=clock or FakeClock())


def test_the_live_data_header_says_it_is_waiting_before_any_data(context):
    window = make()

    header = window.header
    assert (header.title, header.badge, header.style) == (
        "LIVE DATA",
        "WAITING",
        "idle",
    )


def test_it_is_live_once_data_arrives_and_there_is_no_pill_for_it(context):
    window = make()

    window.update({"time": 1.0})

    assert window.feed == "live"
    assert window.header.badge is None, "Green says it is live. No pill is needed."
    assert window.header.style == "running"


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
    first = dpg.get_item_children(window.window_tag, 1)[0]
    assert first == window.header.container, "The header stays at the top."


def test_the_rows_come_before_the_loop_time(context):
    window = make()

    window.update({"time": 1.5})
    window.update({"time": 2.5, "random": 0.25})  # a row added later

    last = dpg.get_item_children(window.card_tag, 1)[-1]
    assert last == window.time_group_tag


# --- the card around the values ---


def theme_of(window):
    return dpg.get_item_theme(window.card_tag)


def test_the_values_are_in_a_card_under_the_header(context):
    window = make()
    window.update({"time": 1.5, "random": 0.25})

    children = dpg.get_item_children(window.window_tag, 1)
    assert children[0] == window.header.container
    assert window.card_tag in children
    assert {"time", "random"} <= {t.strip() for t in texts(window.card_tag)}
    assert dpg.get_item_configuration(window.card_tag)["border"] is True


def test_the_card_fits_its_values(context):
    window = make()
    assert dpg.get_item_configuration(window.card_tag)["auto_resize_y"] is True


def test_the_card_is_grey_before_any_data(context):
    window = make()

    assert window.card_style == "idle"
    assert theme_of(window) == window._themes["idle"]


def test_the_card_has_a_green_border_while_data_arrives(context):
    window = make()

    window.update({"time": 1.0})

    assert window.card_style == "running"
    assert theme_of(window) == window._themes["running"]


def test_the_card_turns_amber_when_the_data_goes_stale_and_green_again(context):
    clock = FakeClock()
    window = make(clock)
    window.update({"time": 1.0})

    clock.now += 10
    window.tick()
    assert theme_of(window) == window._themes["paused"]

    window.update({"time": 2.0})
    assert theme_of(window) == window._themes["running"]


def test_the_header_and_the_card_agree_on_colour(context):
    clock = FakeClock()
    window = make(clock)
    for step in ("nothing", "data", "stale", "data again"):
        if step in ("data", "data again"):
            window.update({"time": 1.0})
        elif step == "stale":
            clock.now += 10
            window.tick()
        assert window.header.style == window.card_style


def test_the_card_uses_the_same_colours_as_the_active_task_card(context):
    """The green border is the same one a running task's card has."""
    from pyacquisition.gui.components.styles import CARD_STYLES

    assert CARD_STYLES["running"]["border"] == (70, 200, 125)
    assert make().feed == "waiting"


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
