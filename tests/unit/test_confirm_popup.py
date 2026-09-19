"""The confirm popup: nothing happens until it is confirmed."""

import dearpygui.dearpygui as dpg
import pytest

from pyacquisition.gui.components.confirm_popup import ConfirmPopup, confirm


@pytest.fixture
def context(monkeypatch):
    dpg.create_context()
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 1000)
    monkeypatch.setattr(dpg, "get_viewport_client_height", lambda: 800)
    yield
    dpg.destroy_context()


class Calls:
    def __init__(self):
        self.confirmed = 0
        self.cancelled = 0

    def on_confirm(self):
        self.confirmed += 1

    def on_cancel(self):
        self.cancelled += 1


def press(button):
    """Press a button, as a click would."""
    dpg.get_item_callback(button)(button, None, None)


def escape(popup):
    """Press the Escape key while the popup is open."""
    (handler,) = dpg.get_item_children(popup._keys, 1)
    dpg.get_item_callback(handler)(handler, None, None)


def texts(item):
    found = []
    for child in dpg.get_item_children(item, 1) or []:
        if dpg.get_item_type(child).endswith("mvText"):
            found.append(dpg.get_value(child))
        found.extend(texts(child))
    return found


def make(calls, **options):
    return ConfirmPopup(
        "Abort it?",
        "This cannot be undone.",
        calls.on_confirm,
        on_cancel=calls.on_cancel,
        **options,
    )


# ---------------------------------------------------------------------------
# Showing it
# ---------------------------------------------------------------------------


def test_it_is_not_showing_until_it_is_shown(context):
    popup = make(Calls())
    assert not popup.is_open


def test_it_shows_a_modal_window_with_the_title_and_message(context):
    popup = make(Calls()).show()

    assert popup.is_open
    assert dpg.get_item_label(popup.tag) == "Abort it?"
    assert dpg.get_item_configuration(popup.tag)["modal"] is True
    assert "This cannot be undone." in texts(popup.tag)


def test_show_returns_the_popup(context):
    popup = make(Calls())
    assert popup.show() is popup


def test_the_buttons_can_be_labelled(context):
    popup = make(Calls(), confirm_label="Abort", cancel_label="Keep going").show()

    assert dpg.get_item_label(popup.confirm_tag) == "Abort"
    assert dpg.get_item_label(popup.cancel_tag) == "Keep going"


def test_the_buttons_are_labelled_confirm_and_cancel_by_default(context):
    popup = make(Calls()).show()

    assert dpg.get_item_label(popup.confirm_tag) == "Confirm"
    assert dpg.get_item_label(popup.cancel_tag) == "Cancel"


def test_it_opens_in_the_middle_of_the_window(context):
    popup = make(Calls()).show()

    x, y = dpg.get_item_pos(popup.tag)
    assert x == (1000 - ConfirmPopup.WIDTH) // 2
    assert 0 < y < 400


def test_a_small_window_does_not_put_it_off_the_edge(context, monkeypatch):
    monkeypatch.setattr(dpg, "get_viewport_client_width", lambda: 100)
    monkeypatch.setattr(dpg, "get_viewport_client_height", lambda: 50)

    x, y = dpg.get_item_pos(make(Calls()).show().tag)

    assert x >= 0 and y >= 0


def test_a_longer_message_gets_a_taller_window(context):
    short = ConfirmPopup("t", "Short.", lambda: None).show()
    long = ConfirmPopup(
        "t", "A much longer message.\n\n" + "word " * 80, lambda: None
    ).show()

    assert dpg.get_item_height(long.tag) > dpg.get_item_height(short.tag)


def test_showing_it_twice_does_not_open_two(context):
    popup = make(Calls()).show()
    tag = popup.tag

    popup.show()

    assert popup.tag == tag
    windows = [
        item
        for item in dpg.get_all_items()
        if dpg.get_item_type(item).endswith("mvWindowAppItem")
    ]
    assert windows.count(tag) == 1


def test_a_dangerous_action_has_a_red_confirm_button(context):
    calm = make(Calls()).show()
    danger = make(Calls(), danger=True).show()

    assert not dpg.get_item_theme(calm.confirm_tag)
    assert dpg.get_item_theme(danger.confirm_tag)
    assert not dpg.get_item_theme(danger.cancel_tag), "Only the confirm button."


# ---------------------------------------------------------------------------
# Answering it
# ---------------------------------------------------------------------------


def test_nothing_happens_until_it_is_confirmed(context):
    calls = Calls()
    make(calls).show()
    assert (calls.confirmed, calls.cancelled) == (0, 0)


def test_confirming_calls_on_confirm_once_and_closes_it(context):
    calls = Calls()
    popup = make(calls).show()

    press(popup.confirm_tag)

    assert (calls.confirmed, calls.cancelled) == (1, 0)
    assert not popup.is_open


def test_cancelling_closes_it_without_confirming(context):
    calls = Calls()
    popup = make(calls).show()

    press(popup.cancel_tag)

    assert (calls.confirmed, calls.cancelled) == (0, 1)
    assert not popup.is_open


def test_cancelling_needs_no_callback(context):
    popup = ConfirmPopup("t", "m", lambda: None).show()  # no on_cancel
    press(popup.cancel_tag)
    assert not popup.is_open


def test_escape_cancels(context):
    calls = Calls()
    popup = make(calls).show()
    (handler,) = dpg.get_item_children(popup._keys, 1)
    assert dpg.get_item_configuration(handler)["key"] == dpg.mvKey_Escape

    escape(popup)

    assert (calls.confirmed, calls.cancelled) == (0, 1)
    assert not popup.is_open


def test_it_can_only_be_answered_once(context):
    calls = Calls()
    popup = make(calls).show()

    popup._confirm()
    popup._confirm()  # a second click that arrives before it closes
    popup._cancel()

    assert (calls.confirmed, calls.cancelled) == (1, 0)


def test_closing_it_removes_the_escape_handler(context):
    popup = make(Calls()).show()
    keys = popup._keys

    popup.close()

    assert not dpg.does_item_exist(keys)
    assert not popup.is_open


def test_close_does_nothing_if_it_is_not_showing(context):
    popup = make(Calls())
    popup.close()  # no error


def test_a_failing_callback_still_closes_it_and_does_not_raise(context):
    def fail():
        raise RuntimeError("could not abort")

    popup = ConfirmPopup("t", "m", fail).show()

    press(popup.confirm_tag)  # no error

    assert not popup.is_open


def test_it_can_be_shown_again_after_it_was_answered(context):
    calls = Calls()
    popup = make(calls).show()
    press(popup.cancel_tag)

    popup.show()
    press(popup.confirm_tag)

    assert (calls.confirmed, calls.cancelled) == (1, 1)


# ---------------------------------------------------------------------------
# The short way to call it
# ---------------------------------------------------------------------------


def test_confirm_shows_the_popup_and_runs_the_action_only_if_confirmed(context):
    calls = Calls()

    popup = confirm("Clear?", "Removes everything.", calls.on_confirm, danger=True)

    assert popup.is_open and calls.confirmed == 0
    press(popup.confirm_tag)
    assert calls.confirmed == 1


def test_confirm_passes_its_options_on(context):
    calls = Calls()

    popup = confirm(
        "Clear?",
        "Removes everything.",
        calls.on_confirm,
        on_cancel=calls.on_cancel,
        confirm_label="Clear",
        cancel_label="No",
    )

    assert dpg.get_item_label(popup.confirm_tag) == "Clear"
    assert dpg.get_item_label(popup.cancel_tag) == "No"
    press(popup.cancel_tag)
    assert calls.cancelled == 1
