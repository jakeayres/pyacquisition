"""The generic card with a label and a checkbox."""

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui.components.checkbox_card import CheckboxCard
from pyacquisition.gui.components.measurement_card import HEIGHT


@pytest.fixture
def context():
    dpg.create_context()
    with dpg.window() as window:
        yield window
    dpg.destroy_context()


def make(window, **options):
    changes = []
    options.setdefault("on_change", changes.append)
    return CheckboxCard(window, 360, label="Start a new block", **options), changes


def test_it_has_a_label_and_a_checkbox_in_a_card_like_an_input_card(context):
    card, _ = make(context, caption="restarts the step")

    assert card.height == HEIGHT
    assert dpg.get_value(card.label_tag) == "Start a new block"
    assert dpg.get_value(card.caption_tag) == "restarts the step"
    assert dpg.get_item_type(card.checkbox_tag).endswith("mvCheckbox")
    assert dpg.get_item_parent(card.checkbox_tag) == card.container


def test_it_starts_unticked_or_ticked(context):
    assert make(context)[0].value is False
    assert make(context, value=True)[0].value is True


def test_clicking_it_reports_whether_it_is_ticked(context):
    card, changes = make(context)

    for ticked in (True, False, True):
        dpg.set_value(card.checkbox_tag, ticked)
        dpg.get_item_callback(card.checkbox_tag)(card.checkbox_tag, ticked, None)

    assert changes == [True, False, True]
    assert card.value is True


def test_setting_it_from_outside_does_not_report(context):
    card, changes = make(context)

    card.set_value(True)

    assert card.value is True and changes == []


def test_nothing_is_drawn_in_it_so_that_the_box_can_be_clicked(context):
    card, _ = make(context)

    kinds = {dpg.get_item_type(c) for c in dpg.get_item_children(card.container, 1)}
    assert not any(kind.endswith("mvDrawlist") for kind in kinds)


def test_the_box_is_at_the_right_and_follows_a_resize(context):
    card, _ = make(context)
    x, _ = dpg.get_item_pos(card.checkbox_tag)
    assert x > 300

    card.resize(240)

    assert dpg.get_item_configuration(card.container)["width"] == 240
    assert dpg.get_item_pos(card.checkbox_tag)[0] < 240


def test_the_label_is_above_the_caption(context):
    card, _ = make(context, caption="a caption")

    assert dpg.get_item_pos(card.label_tag)[1] < dpg.get_item_pos(card.caption_tag)[1]
