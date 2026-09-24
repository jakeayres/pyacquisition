"""The generic card with a label, an input and a submit button."""

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui import Gui
from pyacquisition.gui.components.input_card import KINDS, InputCard
from pyacquisition.gui.components.live_data_window import LiveDataWindow
from pyacquisition.gui.components.measurement_card import HEIGHT


@pytest.fixture
def context():
    dpg.create_context()
    with dpg.window() as window:
        yield window
    dpg.destroy_context()


def make(window, **options):
    sent = []
    options.setdefault("on_submit", sent.append)
    return InputCard(window, 360, label="Period", **options), sent


def test_it_is_about_the_size_of_a_measurement_card_with_the_label_input_and_button(context):
    card, _ = make(context, caption="seconds")

    assert card.height == HEIGHT
    assert dpg.get_value(card.label_tag) == "Period"
    assert dpg.get_value(card.caption_tag) == "seconds"
    assert dpg.get_item_type(card.input_tag).endswith("mvInputFloat")
    assert dpg.get_item_type(card.button_tag).endswith("mvButton")
    for item in (card.input_tag, card.button_tag):
        assert dpg.get_item_parent(item) == card.container


def test_the_button_sends_what_is_in_the_input(context):
    card, sent = make(context, value=1.0)

    dpg.set_value(card.input_tag, 2.5)
    dpg.get_item_callback(card.button_tag)(card.button_tag, None, None)

    assert sent == [2.5]


def test_nothing_is_sent_until_the_button_is_pressed(context):
    card, sent = make(context)

    dpg.set_value(card.input_tag, 9.0)
    dpg.get_item_callback(card.input_tag)(card.input_tag, 9.0, None)

    assert sent == []


def test_the_input_is_not_committed_by_enter(context):
    """An input that commits on Enter puts the old value back when a button is clicked,
    so the button would send what was there before."""
    for kind in KINDS:
        card, _ = make(context, kind=kind, value=1 if kind != "text" else "a")
        assert dpg.get_item_configuration(card.input_tag).get("on_enter") in (False, None)


@pytest.mark.parametrize(
    "kind, value, typed, sent",
    [("float", 1.0, 0.25, 0.25), ("int", 3, 7, 7), ("text", "a", "hello", "hello")],
)
def test_it_takes_floats_ints_and_text(context, kind, value, typed, sent):
    card, got = make(context, kind=kind, value=value)

    dpg.set_value(card.input_tag, typed)
    card._submit()

    assert got == [sent]


def test_an_unknown_kind_is_refused(context):
    with pytest.raises(ValueError, match="float, int, text"):
        make(context, kind="date")


def test_a_number_is_kept_between_the_minimum_and_the_maximum(context):
    card, sent = make(context, minimum=0.001, maximum=10)

    dpg.set_value(card.input_tag, -5.0)
    card._submit()
    dpg.set_value(card.input_tag, 99.0)
    card._submit()

    assert sent == [0.001, 10]
    assert dpg.get_value(card.input_tag) == 10, "It shows what was sent."


def test_a_value_from_outside_does_not_overwrite_what_has_been_typed(context):
    card, _ = make(context, value=1.0)

    card.set_value(2.0)
    assert dpg.get_value(card.input_tag) == 2.0

    dpg.set_value(card.input_tag, 5.0)
    dpg.get_item_callback(card.input_tag)(card.input_tag, 5.0, None)
    card.set_value(3.0)
    assert dpg.get_value(card.input_tag) == 5.0, "Typed and not sent, so left alone."

    card._submit()
    card.set_value(3.0)
    assert dpg.get_value(card.input_tag) == 3.0, "Sent, so the server may change it."


def test_a_value_can_be_forced_in(context):
    card, _ = make(context, value=1.0)
    dpg.get_item_callback(card.input_tag)(card.input_tag, 5.0, None)

    card.set_value(3.0, force=True)

    assert dpg.get_value(card.input_tag) == 3.0


def test_it_can_be_resized_and_keeps_its_controls_at_the_right(context):
    card, _ = make(context)

    card.resize(300)

    assert dpg.get_item_configuration(card.container)["width"] == 300
    x, _ = dpg.get_item_pos(card.button_tag)
    assert x + dpg.get_item_configuration(card.button_tag)["width"] < 300


def test_a_long_label_is_cut_short_to_leave_room_for_the_controls(context):
    card, _ = make(context, caption="")
    card.label = "A really rather long label for this card"
    card.resize(300)

    assert dpg.get_value(card.label_tag).endswith("...")


# ---- in the Live Data window ----


def test_the_live_data_window_has_a_measurement_period_card_when_it_can_set_one(context):
    sent = []
    window = LiveDataWindow(on_period=sent.append)

    card = window.period_card
    assert dpg.get_value(card.label_tag) == "Measurement Period"
    dpg.set_value(card.input_tag, 0.5)
    card._submit()
    assert sent == [0.5]
    assert card.minimum > 0, "A period of zero or less cannot be sent."


def test_without_a_way_to_set_it_there_is_no_period_card(context):
    window = LiveDataWindow()

    assert window.period_card is None
    window.set_period(2.0)  # and it is not an error


def test_the_period_card_follows_the_window_width(context, monkeypatch):
    window = LiveDataWindow(on_period=lambda seconds: None)
    full = window.period_card.width

    monkeypatch.setattr(dpg, "get_y_scroll_max", lambda item: 100)  # a scroll bar
    window._fit()

    assert window.period_card.width == full - 14
    assert window.period_card.width == window.header.width


def test_the_period_the_experiment_reports_is_shown(context):
    window = LiveDataWindow(on_period=lambda seconds: None)

    window.set_period(0.25)

    assert dpg.get_value(window.period_card.input_tag) == 0.25


def test_the_gui_sets_the_period_and_shows_what_the_experiment_has(context):
    gui = Gui()
    gui.live_data_window = LiveDataWindow(on_period=gui._set_measurement_period)
    requests = []

    def get(endpoint, params=None, **kwargs):
        requests.append((endpoint, params))
        return {"paused": False, "period": 0.5}

    gui.api_client.get = get

    dpg.set_value(gui.live_data_window.period_card.input_tag, 0.5)
    gui.live_data_window.period_card._submit()

    assert requests == [("/rack/period/set/", {"period": 0.5}), ("/rack/state", None)]
    assert dpg.get_value(gui.live_data_window.period_card.input_tag) == 0.5


def test_the_polled_state_updates_pause_and_period(context):
    gui = Gui()
    gui.live_data_window = LiveDataWindow(on_period=lambda seconds: None)

    gui._show_rack_state({"paused": True, "period": 2.0})

    assert gui.live_data_window.paused
    assert dpg.get_value(gui.live_data_window.period_card.input_tag) == 2.0


def test_nothing_is_drawn_in_the_card_so_that_nothing_covers_the_controls(context):
    """A drawing takes the mouse from whatever is on top of it, so an input or a
    button on a drawing could never be clicked. The tint is the fill of the card, and
    there is no bar at its left, which sets it apart from a measurement."""
    card, _ = make(context)

    assert not hasattr(card, "drawlist")
    kinds = {
        dpg.get_item_type(child) for child in dpg.get_item_children(card.container, 1)
    }
    assert not any(kind.endswith("mvDrawlist") for kind in kinds)


def test_the_label_is_above_the_caption_and_both_look_centred_in_the_card(context):
    from pyacquisition.gui.components.control_card import TEXT_LIFT
    from pyacquisition.gui.components.measurement_card import INK_DROP

    card, _ = make(context, caption="seconds")

    label_y = dpg.get_item_pos(card.label_tag)[1]
    caption_y = dpg.get_item_pos(card.caption_tag)[1]
    assert label_y < caption_y, "The primary label is above the secondary one."
    # what is seen is lower than the box of the text, by INK_DROP, and by TEXT_LIFT
    # where the controls beside it push the text down
    seen = (label_y + caption_y + 13) / 2 + INK_DROP + TEXT_LIFT
    assert abs(seen - card.height / 2) <= 1.5, "Centred on the card."


def test_a_single_line_looks_centred_in_the_card(context):
    from pyacquisition.gui.components.control_card import TEXT_LIFT
    from pyacquisition.gui.components.measurement_card import INK_DROP

    card, _ = make(context)

    y = dpg.get_item_pos(card.label_tag)[1]
    assert abs(y + 13 / 2 + INK_DROP + TEXT_LIFT - card.height / 2) <= 1.5


# ---- in the Live Data window ----


def test_the_live_data_window_has_a_measurement_period_card_when_it_can_set_one(context):
    sent = []
    window = LiveDataWindow(on_period=sent.append)

    card = window.period_card
    assert dpg.get_value(card.label_tag) == "Measurement Period"
    dpg.set_value(card.input_tag, 0.5)
    card._submit()
    assert sent == [0.5]
    assert card.minimum > 0, "A period of zero or less cannot be sent."


def test_without_a_way_to_set_it_there_is_no_period_card(context):
    window = LiveDataWindow()

    assert window.period_card is None
    window.set_period(2.0)  # and it is not an error


def test_the_period_card_follows_the_window_width(context, monkeypatch):
    window = LiveDataWindow(on_period=lambda seconds: None)
    full = window.period_card.width

    monkeypatch.setattr(dpg, "get_y_scroll_max", lambda item: 100)  # a scroll bar
    window._fit()

    assert window.period_card.width == full - 14
    assert window.period_card.width == window.header.width


def test_the_period_the_experiment_reports_is_shown(context):
    window = LiveDataWindow(on_period=lambda seconds: None)

    window.set_period(0.25)

    assert dpg.get_value(window.period_card.input_tag) == 0.25


def test_the_gui_sets_the_period_and_shows_what_the_experiment_has(context):
    gui = Gui()
    gui.live_data_window = LiveDataWindow(on_period=gui._set_measurement_period)
    requests = []

    def get(endpoint, params=None, **kwargs):
        requests.append((endpoint, params))
        return {"paused": False, "period": 0.5}

    gui.api_client.get = get

    dpg.set_value(gui.live_data_window.period_card.input_tag, 0.5)
    gui.live_data_window.period_card._submit()

    assert requests == [("/rack/period/set/", {"period": 0.5}), ("/rack/state", None)]
    assert dpg.get_value(gui.live_data_window.period_card.input_tag) == 0.5


def test_the_polled_state_updates_pause_and_period(context):
    gui = Gui()
    gui.live_data_window = LiveDataWindow(on_period=lambda seconds: None)

    gui._show_rack_state({"paused": True, "period": 2.0})

    assert gui.live_data_window.paused
    assert dpg.get_value(gui.live_data_window.period_card.input_tag) == 2.0


def test_nothing_is_drawn_in_the_card_so_that_nothing_covers_the_controls(context):
    """A drawing takes the mouse from whatever is on top of it, so an input or a
    button on a drawing could never be clicked. The tint is the fill of the card, and
    there is no bar at its left, which sets it apart from a measurement."""
    card, _ = make(context)

    assert not hasattr(card, "drawlist")
    kinds = {
        dpg.get_item_type(child) for child in dpg.get_item_children(card.container, 1)
    }
    assert not any(kind.endswith("mvDrawlist") for kind in kinds)


def test_it_can_be_an_input_with_no_button(context):
    changes = []
    card, sent = make(
        context, kind="text", value="cold", button_label=None, on_change=changes.append
    )

    assert card.button_tag is None
    assert dpg.get_item_type(card.input_tag).endswith("mvInputText")
    dpg.set_value(card.input_tag, "warm")
    dpg.get_item_callback(card.input_tag)(card.input_tag, "warm", None)

    assert changes == ["warm"] and sent == []
    assert card.value == "warm"


def test_an_input_with_no_button_sits_at_the_right_edge(context):
    with_button, _ = make(context)
    without, _ = make(context, button_label=None)

    edge = 360 - 10  # the width of the card, less the space at its right
    x, _ = dpg.get_item_pos(without.input_tag)
    assert x + dpg.get_item_configuration(without.input_tag)["width"] == edge
    assert x > dpg.get_item_pos(with_button.input_tag)[0], "It takes the button's place."
