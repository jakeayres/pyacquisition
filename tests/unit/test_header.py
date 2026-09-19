"""The header strip used at the top of each pane."""

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui.components.header import (
    CHAR_WIDTH,
    TEXT_HEIGHT,
    PaneHeader,
    fit,
    text_width,
)
from pyacquisition.gui.constants import STATE_STYLES


@pytest.fixture
def window():
    dpg.create_context()
    with dpg.window(width=420, height=300) as window:
        yield window
    dpg.destroy_context()


def shown(item):
    """The text an item of the header is drawing."""
    return dpg.get_item_configuration(item)["text"]


def visible(item):
    return dpg.get_item_configuration(item)["show"]


def colour(item, key):
    """A colour of an item as 0 to 255. DearPyGui reports it as 0 to 1."""
    return tuple(round(c * 255) for c in dpg.get_item_configuration(item)[key][:3])


# ---------------------------------------------------------------------------
# Measuring and shortening text
# ---------------------------------------------------------------------------


def test_text_width_is_seven_pixels_a_character_at_the_normal_size():
    assert text_width("RUNNING") == 49
    assert text_width("") == 0


def test_text_width_is_a_whole_number_of_pixels():
    assert isinstance(text_width("abc"), int)
    assert text_width("abc") == 3 * CHAR_WIDTH


def test_text_that_fits_is_unchanged():
    assert fit("furnace PID", 200) == "furnace PID"


def test_text_that_does_not_fit_is_shortened_with_dots():
    result = fit("a very long task name", 100)
    assert result.endswith("...")
    assert text_width(result) <= 100


def test_text_is_dropped_if_there_is_no_room_for_anything():
    assert fit("anything", 10) == ""
    assert fit("anything", 0) == ""


# ---------------------------------------------------------------------------
# What it draws
# ---------------------------------------------------------------------------


def test_it_draws_the_title_subtitle_and_badge(window):
    header = PaneHeader(
        window, 400, title="CONTROL", subtitle="furnace PID", badge="RUNNING"
    )

    assert shown(header._title) == "CONTROL"
    assert shown(header._subtitle) == "furnace PID"
    assert shown(header._badge_text) == "RUNNING"
    assert visible(header._badge_rect) and visible(header._badge_text)


def test_without_a_badge_there_is_no_pill(window):
    header = PaneHeader(window, 400, title="LIVE DATA")

    assert not visible(header._badge_rect)
    assert not visible(header._badge_text)


def test_without_a_subtitle_there_is_none_showing(window):
    header = PaneHeader(window, 400, title="LIVE DATA")
    assert not visible(header._subtitle)


def test_the_subtitle_sits_after_the_title(window):
    header = PaneHeader(window, 400, title="CONTROL", subtitle="furnace PID")

    title_x = dpg.get_item_configuration(header._title)["pos"][0]
    subtitle_x = dpg.get_item_configuration(header._subtitle)["pos"][0]
    assert subtitle_x >= title_x + text_width("CONTROL")


def test_the_badge_is_at_the_right_edge(window):
    header = PaneHeader(window, 400, title="X", badge="RUNNING")

    right = dpg.get_item_configuration(header._badge_rect)["pmax"][0]
    assert right == 400 - 10


def test_a_header_with_a_caption_shows_it_and_is_taller(window):
    plain = PaneHeader(window, 400, title="05.00 start.data")
    captioned = PaneHeader(window, 400, title="05.00 start.data", caption="DATA FILE")

    assert captioned.height > plain.height
    assert shown(captioned._caption) == "DATA FILE"
    assert visible(captioned._caption)
    assert not visible(plain._caption)


def test_a_long_title_is_shortened_and_leaves_no_room_for_the_subtitle(window):
    header = PaneHeader(
        window,
        300,
        title="A_VERY_LONG_MANAGER_NAME_INDEED",
        subtitle="task",
        badge="RUNNING",
    )

    assert shown(header._title).endswith("...")
    assert not visible(header._subtitle)


def test_a_long_subtitle_is_shortened_to_fit(window):
    header = PaneHeader(
        window,
        400,
        title="MAIN",
        subtitle="a task with a really rather long name",
        badge="RUNNING",
    )

    assert shown(header._subtitle).endswith("...")
    left = dpg.get_item_configuration(header._subtitle)["pos"][0]
    badge_left = dpg.get_item_configuration(header._badge_rect)["pmin"][0]
    assert left + text_width(shown(header._subtitle)) <= badge_left


# ---------------------------------------------------------------------------
# Sharp text
# ---------------------------------------------------------------------------
#
# The font is a small pixel font. Drawn at any other size than its own, or between
# two pixels, it goes blurry.

CASES = [
    dict(title="MAIN", subtitle="WaitFor", badge="RUNNING", style="running"),
    dict(
        title="CONTROL",
        subtitle="furnace PID",
        badge="ABORTING",
        style="aborting",
        collapsible=True,
    ),
    dict(
        title="A_VERY_LONG_MANAGER_NAME",
        subtitle="a long task name here",
        badge="PAUSED",
        style="paused",
        collapsible=True,
    ),
    dict(title="05.00 start.data", caption="DATA FILE"),
    dict(title="LIVE DATA", badge="WAITING", style="idle"),
    dict(title="X"),
]


def text_items(header):
    return [header._caption, header._title, header._subtitle, header._badge_text]


def whole(numbers):
    return all(float(n).is_integer() for n in numbers)


@pytest.mark.parametrize("options", CASES)
@pytest.mark.parametrize("width", [284, 372, 384, 301])
def test_all_text_is_drawn_at_the_size_of_the_font(window, options, width):
    header = PaneHeader(window, width, **options)

    for item in text_items(header):
        assert dpg.get_item_configuration(item)["size"] == TEXT_HEIGHT


@pytest.mark.parametrize("options", CASES)
@pytest.mark.parametrize("width", [284, 372, 384, 301])
def test_everything_is_placed_on_whole_pixels(window, options, width):
    header = PaneHeader(window, width, **options)

    for item in text_items(header):
        assert whole(dpg.get_item_configuration(item)["pos"]), item
    for item in (header._badge_rect, header._background, header._accent):
        config = dpg.get_item_configuration(item)
        assert whole(config["pmin"]) and whole(config["pmax"]), item


def test_text_stays_at_the_size_of_the_font_as_it_changes(window):
    header = PaneHeader(window, 384, title="MAIN", caption=None)

    for title, subtitle, badge in [
        ("MAIN", "WaitFor", "RUNNING"),
        ("CONTROL", "a task with a rather long name", "ABORTING"),
        ("A_VERY_LONG_MANAGER_NAME_INDEED", "x", "PAUSED"),
    ]:
        header.update(title, subtitle=subtitle, badge=badge, style="running")
        for item in text_items(header):
            assert dpg.get_item_configuration(item)["size"] == TEXT_HEIGHT
            assert whole(dpg.get_item_configuration(item)["pos"])


def test_it_stays_sharp_after_being_resized(window):
    header = PaneHeader(window, 384, title="MAIN", subtitle="WaitFor", badge="RUNNING")

    header.resize(370)

    for item in text_items(header):
        assert dpg.get_item_configuration(item)["size"] == TEXT_HEIGHT
        assert whole(dpg.get_item_configuration(item)["pos"])


def test_the_title_and_subtitle_share_a_line(window):
    header = PaneHeader(window, 384, title="MAIN", subtitle="WaitFor", badge="RUNNING")

    title_y = dpg.get_item_configuration(header._title)["pos"][1]
    subtitle_y = dpg.get_item_configuration(header._subtitle)["pos"][1]
    badge_y = dpg.get_item_configuration(header._badge_text)["pos"][1]
    assert title_y == subtitle_y == badge_y


def test_the_text_sits_inside_the_header(window):
    for options in CASES:
        header = PaneHeader(window, 384, **options)
        for item in text_items(header):
            config = dpg.get_item_configuration(item)
            if config["show"]:
                assert 0 <= config["pos"][1] <= header.height - TEXT_HEIGHT


# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("style", list(STATE_STYLES))
def test_the_colours_come_from_the_style(window, style):
    header = PaneHeader(window, 400, title="X", badge="B", style=style)

    assert colour(header._background, "fill") == STATE_STYLES[style]["background"]
    assert colour(header._accent, "fill") == STATE_STYLES[style]["border"]
    assert colour(header._badge_rect, "fill") == STATE_STYLES[style]["border"]


def test_update_changes_the_text_and_the_colours(window):
    header = PaneHeader(
        window, 400, title="CONTROL", subtitle="a", badge="RUNNING", style="running"
    )

    header.update("CONTROL", subtitle="b", badge="PAUSED", style="paused")

    assert shown(header._subtitle) == "b"
    assert shown(header._badge_text) == "PAUSED"
    assert colour(header._accent, "fill") == STATE_STYLES["paused"]["border"]
    assert (header.subtitle, header.badge, header.style) == ("b", "PAUSED", "paused")


def test_update_can_remove_the_badge(window):
    header = PaneHeader(window, 400, title="X", badge="LIVE", style="running")

    header.update("X", badge=None, style="neutral")

    assert not visible(header._badge_rect)


def test_update_changes_the_caption_only_if_it_has_one(window):
    plain = PaneHeader(window, 400, title="X")
    captioned = PaneHeader(window, 400, title="X", caption="DATA FILE")

    plain.update("X", caption="ignored")
    captioned.update("Y", caption="OTHER")

    assert plain.caption is None and not visible(plain._caption)
    assert shown(captioned._caption) == "OTHER"


# ---------------------------------------------------------------------------
# Collapsing, and its width
# ---------------------------------------------------------------------------


def descendants(item):
    for child in dpg.get_item_children(item, 1) or []:
        yield child
        yield from descendants(child)


def click_header(header):
    """Click the header: run the handler that is bound to it."""
    (handler,) = dpg.get_item_children(header._handlers, 1)
    dpg.get_item_callback(handler)(
        handler, (dpg.mvMouseButton_Left, header.drawlist), None
    )


def test_only_a_collapsible_header_has_a_chevron(window):
    plain = PaneHeader(window, 400, title="X")
    collapsible = PaneHeader(window, 400, title="X", collapsible=True)

    assert plain._chevron is None and plain._handlers is None
    assert collapsible._chevron is not None and collapsible._handlers is not None


def test_the_click_is_handled_by_the_header_and_not_by_a_button_on_top_of_it(window):
    """A button placed over the drawing cannot be clicked, because the drawing takes
    the mouse. So there must be none, and the click must be bound to the drawing."""
    header = PaneHeader(window, 400, title="X", collapsible=True)

    assert not any(
        dpg.get_item_type(item).endswith("mvButton")
        for item in descendants(header.container)
    )
    assert dpg.get_item_info(header.drawlist)["handlers"] == header._handlers


def test_a_click_on_the_header_collapses_it_and_a_second_expands_it(window):
    calls = []
    header = PaneHeader(
        window, 400, title="X", collapsible=True, on_collapse=calls.append
    )

    click_header(header)
    assert header.collapsed
    click_header(header)

    assert calls == [True, False]
    assert not header.collapsed


def test_a_header_that_cannot_collapse_ignores_clicks(window):
    header = PaneHeader(window, 400, title="X")
    assert header._handlers is None  # nothing is listening


def chevron_points(header):
    config = dpg.get_item_configuration(header._chevron)
    return [config["p1"], config["p2"], config["p3"]]


def test_the_chevron_points_down_when_open_and_right_when_collapsed(window):
    header = PaneHeader(window, 400, title="X", collapsible=True)

    def points_down():
        (x1, y1), (x2, y2), (x3, y3) = chevron_points(header)
        return y1 == y2 and y3 > y1  # a flat top and a point below it

    def points_right():
        (x1, y1), (x2, y2), (x3, y3) = chevron_points(header)
        return x1 == x2 and x3 > x1  # a flat side and a point to the right of it

    assert points_down()
    click_header(header)
    assert points_right()
    click_header(header)
    assert points_down()


def test_the_chevron_is_drawn_on_whole_pixels_and_inside_the_header(window):
    header = PaneHeader(window, 400, title="X", collapsible=True)

    for _ in range(3):  # open, collapsed, open
        for x, y in chevron_points(header):
            assert float(x).is_integer() and float(y).is_integer()
            assert 0 <= x < 36 and 0 <= y <= header.height
        click_header(header)


def test_a_collapsible_header_leaves_room_for_the_chevron(window):
    plain = PaneHeader(window, 400, title="X")
    collapsible = PaneHeader(window, 400, title="X", collapsible=True)

    x = lambda h: dpg.get_item_configuration(h._title)["pos"][0]
    assert x(collapsible) > x(plain)


def test_clicking_needs_no_listener(window):
    click_header(PaneHeader(window, 400, title="X", collapsible=True))  # no error


def test_resize_changes_the_width_and_moves_the_badge(window):
    header = PaneHeader(window, 400, title="X", badge="RUNNING")

    header.resize(300)

    assert header.width == 300
    assert dpg.get_item_configuration(header.drawlist)["width"] == 300
    assert dpg.get_item_configuration(header._badge_rect)["pmax"][0] == 300 - 10


def test_fit_to_takes_the_width_of_the_window_less_its_padding(window):
    header = PaneHeader(window, 100, title="X")
    header.fit_to(window)
    assert header.width == 420 - 16


def test_fit_to_leaves_room_for_a_scroll_bar(window, monkeypatch):
    header = PaneHeader(window, 100, title="X")
    monkeypatch.setattr(dpg, "get_y_scroll_max", lambda item: 1)

    header.fit_to(window)

    assert header.width == 420 - 16 - 14
