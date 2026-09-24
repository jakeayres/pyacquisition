"""The cards of the Live Data window: their values, names and colours."""

import math
import pickle

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui.components import fonts
from pyacquisition.gui.constants import MUTED_COLOR
from pyacquisition.gui.components.live_data_window import (
    VALUE_FONT_SIZE,
    VALUE_CHARS,
    LiveDataWindow,
    format_value,
)
from pyacquisition.gui.components.numbers import format_number, is_number


@pytest.fixture
def context():
    dpg.create_context()
    yield
    dpg.destroy_context()


class FakeClock:
    now = 100.0

    def __call__(self):
        return self.now


def texts(item):
    found = []
    for child in dpg.get_item_children(item, 1) or []:
        if dpg.get_item_type(child).endswith("mvText"):
            found.append(dpg.get_value(child))
        found.extend(texts(child))
    return found


def make():
    return LiveDataWindow(clock=FakeClock())


# ---------------------------------------------------------------------------
# Numbers as text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, text",
    [
        (0.8405884400988841, "0.8405884401"),
        (-0.7843075691046084, "-0.784307569"),
        (1789978454.496, "1789978454.5"),
        (2.5, "2.5"),
        (40.0, "40"),
        (0.0, "0"),
        (1.5e-9, "1.5e-09"),
        (123456789012345678, "1.23457e+17"),
        (42, "42"),
        (float("nan"), "nan"),
        (float("inf"), "inf"),
    ],
)
def test_a_number_is_shown_in_twelve_characters_or_fewer(value, text):
    assert format_number(value) == text
    assert len(format_number(value)) <= 12


@pytest.mark.parametrize(
    "value, width, text",
    [
        (1789978454.496 + 3 * 250, 18, "1789979204.496"),  # not ...4960001
        (0.8405884400988841, 18, "0.8405884400988841"),  # room for all of it
        (0.1 + 0.2, 18, "0.3"),  # 0.30000000000000004 is 19 characters
        (2.5, 18, "2.5"),
    ],
)
def test_a_wider_column_shows_the_exact_number_and_never_its_noise(value, width, text):
    assert format_number(value, width) == text


def test_a_bool_is_not_a_number_to_draw():
    assert is_number(1) and is_number(1.5)
    assert not is_number(True)
    assert not is_number("1.5") and not is_number(None)


def test_text_is_cut_short_to_its_column():
    assert format_value("ok") == "ok"
    assert format_value("a rather long status string").endswith("...")


# ---------------------------------------------------------------------------
# In the window
# ---------------------------------------------------------------------------


def test_a_value_that_stops_being_a_number_does_not_stop_the_window(context):
    window = make()
    window.update({"x": 1.0})

    window.update({"x": "error"})
    window.update({"x": 2.0})
    window.tick()

    assert "error" not in [t.strip() for t in texts(window.card_tag)]


def test_a_missing_value_does_not_break_the_window(context):
    """A measurement that returns `None` used to raise, because of how it was formatted."""
    window = make()

    window.update({"x": None})
    window.update({"x": None})

    assert "None" in [t.strip() for t in texts(window.card_tag)]


def test_a_long_decimal_is_shortened_so_that_the_values_line_up(context):
    window = make()

    window.update({"random": 0.8405884400988841})

    shown = [t.strip() for t in texts(window.card_tag)]
    assert "0.8405884401" in shown


def test_a_long_name_is_cut_short_to_its_column(context):
    window = make()

    window.update({"a_really_rather_long_measurement_name" * 4: 1.0})

    (name,) = [t for t in texts(window.card_tag) if t.startswith("a_really")]
    assert name.endswith("...")
    card = window.cards["a_really_rather_long_measurement_name" * 4]
    assert len(name) * 7 <= card.width - 26 - 130, "Room is left for the value."


def test_the_value_column_is_as_wide_as_the_shortened_numbers(context):
    assert VALUE_CHARS >= max(len(format_number(v)) for v in (0.5, 1e-9, 1789978454.496))


def rgb(item):
    """The colour of an item, as three numbers from 0 to 255, however DearPyGui gives it."""
    color = dpg.get_item_configuration(item)["color"]
    scale = 255 if max(color) <= 1.0 else 1
    return tuple(round(c * scale) for c in color[:3])


def test_it_works_without_a_large_font(context, monkeypatch):
    """No monospace font is installed. The value is coloured, but no larger."""
    monkeypatch.setattr(fonts, "find_font", lambda candidates=None: None)
    window = make()

    window.update({"x": 20.5})

    assert window._large_font is None
    assert dpg.get_value(window.value_tags["x"]) == "20.5"


def test_no_font_is_loaded_when_there_is_none_to_load(context):
    assert fonts.find_font(("/no/such/font.ttf",)) is None
    assert fonts.add_font(26, ("/no/such/font.ttf",)) is None


def test_there_is_only_one_size(context):
    window = make()

    assert not hasattr(window, "set_size") and not hasattr(window, "size")
    assert not hasattr(window, "sparklines")


def test_a_line_has_a_white_name_and_a_large_coloured_value(context):
    window = make()

    window.update({"a": 1.0, "b": 2.0})

    for key in ("a", "b"):
        assert rgb(window.key_tags[key]) == (255, 255, 255)
        assert rgb(window.value_tags[key]) == tuple(window.colors[key])
    assert window.colors["a"] != window.colors["b"]


def test_a_small_card_shows_where_a_measurement_comes_from_in_grey(context):
    window = LiveDataWindow(clock=FakeClock(), sources={"a": "cryo.get_temperature"})

    window.update({"a": 1.0, "b": 2.0})

    assert dpg.get_value(window.cards["a"].source_tag) == "cryo.get_temperature"
    assert rgb(window.cards["a"].source_tag) == MUTED_COLOR
    assert dpg.get_item_configuration(window.cards["b"].source_tag)["show"] is False


def test_a_measurement_says_which_instrument_and_method_it_comes_from():
    from functools import partial

    from pyacquisition.core.measurement import Measurement

    class Instrument:
        _uid = "cryo"

        def get_temperature(self, input_channel=1):
            return 4.2

    instrument = Instrument()
    assert Measurement("T", instrument.get_temperature).source == "cryo.get_temperature"
    query = partial(Instrument.get_temperature, instrument)
    assert Measurement("T", partial(query, input_channel=2)).source == (
        "cryo.get_temperature"
    )
    assert Measurement("t", lambda: 1).source == ""
