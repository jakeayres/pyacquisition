"""The generic card that is only a button."""

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui.components.button_card import HEIGHT, MARGIN, ButtonCard


@pytest.fixture
def context():
    dpg.create_context()
    with dpg.window() as window:
        yield window
    dpg.destroy_context()


def make(window, **options):
    clicks = []
    options.setdefault("on_click", lambda: clicks.append("clicked"))
    return ButtonCard(window, 360, label="Next File", **options), clicks


def test_it_is_a_card_with_a_button_that_fills_it(context):
    card, _ = make(context)

    assert card.height == HEIGHT
    assert dpg.get_item_label(card.button_tag) == "Next File"
    assert dpg.get_item_configuration(card.button_tag)["width"] == 360 - 2 * MARGIN
    assert dpg.get_item_pos(card.button_tag)[0] == MARGIN
    assert dpg.get_item_parent(card.button_tag) == card.container


def test_it_is_only_a_button(context):
    card, _ = make(context)

    shown = [
        dpg.get_value(child)
        for child in dpg.get_item_children(card.container, 1)
        if dpg.get_item_type(child).endswith("mvText") and dpg.get_item_configuration(child)["show"]
    ]
    assert [text for text in shown if text] == [], "No label or caption of its own."


def test_pressing_it_calls_back_with_no_arguments(context):
    card, clicks = make(context)

    dpg.get_item_callback(card.button_tag)(card.button_tag, None, None)
    dpg.get_item_callback(card.button_tag)(card.button_tag, None, None)

    assert clicks == ["clicked", "clicked"]


def test_it_follows_a_resize(context):
    card, _ = make(context)

    card.resize(240)

    assert dpg.get_item_configuration(card.container)["width"] == 240
    assert dpg.get_item_configuration(card.button_tag)["width"] == 240 - 2 * MARGIN


def test_it_can_be_disabled(context):
    card, _ = make(context, enabled=False)
    assert dpg.get_item_configuration(card.button_tag)["enabled"] is False

    card.set_enabled(True)

    assert dpg.get_item_configuration(card.button_tag)["enabled"] is True


def test_nothing_is_drawn_in_it_so_that_the_button_can_be_clicked(context):
    card, _ = make(context)

    kinds = {dpg.get_item_type(c) for c in dpg.get_item_children(card.container, 1)}
    assert not any(kind.endswith("mvDrawlist") for kind in kinds)
