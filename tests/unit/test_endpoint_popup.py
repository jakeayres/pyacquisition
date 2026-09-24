"""The window that calls an endpoint of the API, and the requests it sends."""

import threading

import dearpygui.dearpygui as dpg
import pytest
import requests

from pyacquisition.gui.api_client import APIClient, Reply, describe_error
from pyacquisition.gui.components import endpoint_popup as ep
from pyacquisition.gui.components.endpoint_popup import EndpointPopup
from pyacquisition.gui.openapi import Schema


@pytest.fixture
def context():
    dpg.create_context()
    yield
    dpg.destroy_context()


def parameter(name, schema, required=True):
    return {"name": name, "in": "query", "required": required, "schema": schema}


def make_path(address="/keithley/set_current", summary="Set Current", **options):
    method = {"summary": summary, "parameters": options.pop("parameters", [])}
    method.update(options)
    return Schema({"paths": {address: {"get": method}}}).paths[address]


class FakeClient:
    """Remembers requests, and answers them when told to."""

    def __init__(self):
        self.requests = []

    def get_async(self, endpoint, callback, params=None, timeout=30.0):
        self.requests.append((endpoint, callback, params))

    def answer(self, reply, index=-1):
        self.requests[index][1](reply)


def texts(item):
    found = []
    for child in dpg.get_item_children(item, 1) or []:
        if dpg.get_item_type(child).endswith("mvText"):
            found.append(dpg.get_value(child))
        found.extend(texts(child))
    return found


def press(button):
    dpg.get_item_callback(button)(button, None, None)


def popup_for(path, client=None):
    popup = EndpointPopup(client or FakeClient(), path)
    popup.draw()
    return popup


CURRENT = [
    parameter("current", {"type": "number"}),
    parameter("channel", {"type": "integer"}),
    parameter("mode", {"type": "string", "enum": ["dc", "ac"]}),
    parameter("enabled", {"type": "boolean"}),
]


# ---------------------------------------------------------------------------
# Working out what to show
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "address, caption",
    [
        ("/keithley/get_voltage", "KEITHLEY"),
        ("/rack/list_instruments", "RACK"),
        ("/task_manager/pause", "TASK MANAGER"),
        ("/tasks/ramp", "TASKS"),
        ("/managers/sweeps/pause", "SWEEPS · TASK MANAGER"),
        ("/managers/sweeps/tasks/ramp", "SWEEPS · TASKS"),
        ("/managers", "TASK MANAGER"),
    ],
)
def test_the_caption_says_what_the_endpoint_belongs_to(address, caption):
    assert ep.caption_for(address) == caption


def test_the_main_task_manager_is_named_when_it_is_told_to_be():
    """Its addresses do not say which it is, so with several the menu tells the popup."""
    assert ep.caption_for("/task_manager/pause", "main") == "MAIN · TASK MANAGER"
    assert ep.caption_for("/tasks/hold", "main") == "MAIN · TASKS"
    assert ep.caption_for("/keithley/get_voltage", "main") == "KEITHLEY"


def test_the_wrapper_of_a_reply_is_removed():
    assert ep.unwrap({"status": 200, "data": 1.5}) == 1.5
    assert ep.unwrap({"status": 200, "data": {"a": 1}}) == {"a": 1}


def test_a_reply_with_other_keys_is_left_alone():
    assert ep.unwrap({"data": 1, "extra": 2}) == {"data": 1, "extra": 2}
    assert ep.unwrap(["a", "b"]) == ["a", "b"]


def test_decimals_are_shortened_but_not_to_the_screen_precision():
    assert ep.scalar_text(0.1 + 0.2) == "0.3"
    assert ep.scalar_text(1.23456789012e-06) == "1.23456789e-06"
    assert ep.scalar_text(None) == "None"


def test_a_dictionary_and_a_list_are_rows():
    assert ep.rows_of({"x": 1, "y": 2.5}) == [("x", "1"), ("y", "2.5")]
    assert ep.rows_of(["a", "b"]) == [("[0]", "a"), ("[1]", "b")]


def test_a_single_value_and_an_empty_one_are_not_rows():
    assert ep.rows_of(3) is None
    assert ep.rows_of("text") is None
    assert ep.rows_of([]) is None
    assert ep.rows_of({}) is None


def test_an_entry_is_not_shortened_until_it_is_shown():
    ((_, text),) = ep.rows_of({"k": "x" * 200})
    assert text == "x" * 200


def test_a_long_entry_is_shortened_to_fit_the_card(context):
    """It was cut off by the edge of the card, part way through a word."""
    client = FakeClient()
    popup = popup_for(make_path(), client)
    popup.request()

    client.answer(Reply(True, {"status": 200, "data": {"instruments": "x" * 200}}))

    shown = texts(popup.result_tag)
    (value,) = [text for text in shown if text.startswith("xx")]
    assert len(value) == ep.cell_room(len("instruments"))
    assert value.endswith("...")
    # name, space and value all fit in the width of the card
    assert (len("instruments") + 1 + len(value)) * ep.CHAR_WIDTH <= ep.CONTENT_WIDTH


def test_the_whole_reply_is_copied_not_the_shortened_one():
    assert "x" * 200 in ep.copy_text({"k": "x" * 200})
    assert ep.copy_text("plain") == "plain"
    assert ep.copy_text(1.5) == "1.5"


def test_only_the_first_paragraph_of_a_description_is_shown():
    shown, whole = ep.describe("Set the\ncurrent.\n\nArgs:\n    current: amps.")
    assert shown == "Set the current."
    assert whole.endswith("amps.")
    assert ep.describe(None) == ("", "")


# ---------------------------------------------------------------------------
# The window
# ---------------------------------------------------------------------------


def test_the_window_is_named_by_its_address_and_the_header_by_its_endpoint(context):
    popup = popup_for(make_path())

    assert popup.title == "Set Current"
    assert popup.caption == "KEITHLEY"
    assert dpg.get_item_label(popup.uuid) == "/keithley/set_current"


def test_there_is_an_input_for_each_parameter_of_the_right_kind(context):
    popup = popup_for(make_path(parameters=CURRENT))

    inputs = popup.input_group.inputs
    kinds = [dpg.get_item_type(i.uuid).split("::")[-1] for i in inputs]
    assert kinds == ["mvInputDouble", "mvInputInt", "mvCombo", "mvCheckbox"]
    assert [i.label for i in inputs] == ["current", "channel", "mode", "enabled"]


def test_a_parameter_of_an_unknown_type_becomes_a_text_box(context):
    path = make_path(parameters=[parameter("thing", {"anyOf": [{"type": "array"}]})])
    popup = popup_for(path)

    (component,) = popup.input_group.inputs
    assert dpg.get_item_type(component.uuid).endswith("mvInputText")


def test_a_float_box_is_double_precision(context):
    """A single precision box turns 1e-9 into 9.99999971718e-10 before it is sent."""
    popup = popup_for(make_path(parameters=[parameter("i", {"type": "number"})]))
    (component,) = popup.input_group.inputs

    dpg.set_value(component.uuid, 1e-9)

    assert popup.get_input_data() == {"i": 1e-9}


def test_there_is_no_reply_card_before_anything_is_sent(context):
    popup = popup_for(make_path(parameters=CURRENT))

    assert not dpg.get_item_configuration(popup.result_tag)["show"]
    assert "Response" not in texts(popup.uuid)


def test_a_window_with_no_parameters_has_no_form(context):
    popup = popup_for(make_path(address="/k/get_voltage", summary="Get Voltage"))

    assert popup.input_group.length == 0
    assert dpg.get_item_label(popup.send_tag) == "Send Request"


def test_a_long_docstring_shows_only_its_first_paragraph(context):
    path = make_path(description="Set the current.\n\nArgs:\n    current: amps.")
    popup = popup_for(path)

    visible = [
        dpg.get_value(child)
        for child in dpg.get_item_children(popup.uuid, 1)
        if dpg.get_item_type(child).endswith("mvText")
    ]
    assert visible == ["Set the current."]


def test_closing_the_window_deletes_it_and_its_themes(context):
    popup = popup_for(make_path())
    themes = [*popup._themes.values(), *popup._extra_themes]
    assert themes and all(dpg.does_item_exist(t) for t in themes)

    popup.close()

    assert not popup.is_open
    assert not any(dpg.does_item_exist(t) for t in themes)


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------


def test_send_request_sends_what_is_in_the_form(context):
    client = FakeClient()
    popup = popup_for(make_path(parameters=CURRENT), client)
    current, channel, mode, enabled = popup.input_group.inputs
    dpg.set_value(current.uuid, 2.5)
    dpg.set_value(channel.uuid, 3)
    dpg.set_value(mode.uuid, "ac")
    dpg.set_value(enabled.uuid, True)

    press(popup.send_tag)

    ((endpoint, _, params),) = client.requests
    assert endpoint == "/keithley/set_current"
    assert params == {"current": 2.5, "channel": 3, "mode": "ac", "enabled": True}


def test_a_box_keeps_what_is_typed_when_the_send_button_is_clicked(context):
    """
    A box made with `on_enter=True` keeps what is typed only when Enter is pressed. If
    the Send button is clicked instead, it puts back the old value, and the request is
    sent with that: a WaitFor of 2 minutes was queued as 0 hours, 0 minutes and 0
    seconds, which finishes at once. A box must keep what is typed as it is typed.
    """
    path = make_path(parameters=[*CURRENT, parameter("note", {"type": "string"})])
    popup = popup_for(path)

    for component in popup.input_group.inputs:
        config = dpg.get_item_configuration(component.uuid)
        assert config.get("on_enter", False) is False, component.label


def test_the_button_is_disabled_until_the_reply_comes(context):
    client = FakeClient()
    popup = popup_for(make_path(), client)

    press(popup.send_tag)

    assert dpg.get_item_label(popup.send_tag) == "Sending..."
    assert not dpg.get_item_configuration(popup.send_tag)["enabled"]

    client.answer(Reply(True, {"status": 200, "data": 1}))

    assert dpg.get_item_label(popup.send_tag) == "Send Request"
    assert dpg.get_item_configuration(popup.send_tag)["enabled"]


def test_a_second_request_is_not_sent_while_one_is_out(context):
    client = FakeClient()
    popup = popup_for(make_path(), client)

    popup.request()
    popup.request()

    assert len(client.requests) == 1


def test_a_value_is_shown_without_its_wrapper(context):
    client = FakeClient()
    popup = popup_for(make_path(), client)
    popup.request()

    client.answer(Reply(True, {"status": 200, "data": 0.5}, elapsed=0.041))

    shown = texts(popup.result_tag)
    assert "OK" in shown
    assert "0.5" in shown
    assert shown[1].startswith("41 ms")
    assert dpg.get_item_configuration(popup.result_tag)["show"]
    assert not any("status" in text for text in shown)


def test_a_dictionary_is_shown_as_rows(context):
    client = FakeClient()
    popup = popup_for(make_path(), client)
    popup.request()

    client.answer(Reply(True, {"status": 200, "data": {"x": 1.5, "unit": "V"}}))

    shown = texts(popup.result_tag)
    assert "x   " in shown  # padded, so that the values line up
    assert "unit" in shown
    assert "1.5" in shown
    assert "V" in shown


def test_a_long_list_is_cut_short_and_says_so(context):
    client = FakeClient()
    popup = popup_for(make_path(), client)
    popup.request()

    client.answer(Reply(True, {"status": 200, "data": list(range(25))}))

    shown = texts(popup.result_tag)
    assert f"[{ep.MAX_ROWS - 1}]" in shown
    assert f"[{ep.MAX_ROWS}]" not in shown
    assert any(f"and {25 - ep.MAX_ROWS} more" in text for text in shown)


def test_an_error_is_shown_with_what_went_wrong(context):
    client = FakeClient()
    popup = popup_for(make_path(), client)
    popup.request()

    client.answer(Reply(False, error="kelvin: Input should be a valid number"))

    shown = texts(popup.result_tag)
    assert "ERROR" in shown
    assert "kelvin: Input should be a valid number" in shown
    assert popup.last_reply.ok is False


def test_the_card_changes_colour_with_the_reply(context):
    client = FakeClient()
    popup = popup_for(make_path(), client)

    popup.request()
    client.answer(Reply(True, {"status": 200, "data": 1}))
    ok = dpg.get_item_theme(popup.result_tag)
    popup.request()
    client.answer(Reply(False, error="no"))

    assert ok == popup._themes["running"]
    assert dpg.get_item_theme(popup.result_tag) == popup._themes["aborting"]


def test_a_new_reply_replaces_the_last_one(context):
    client = FakeClient()
    popup = popup_for(make_path(), client)

    popup.request()
    client.answer(Reply(True, {"status": 200, "data": "first"}))
    popup.request()
    client.answer(Reply(True, {"status": 200, "data": "second"}))

    shown = texts(popup.result_tag)
    assert "second" in shown
    assert "first" not in shown


def test_a_reply_that_comes_after_the_window_closed_is_ignored(context):
    client = FakeClient()
    popup = popup_for(make_path(), client)
    popup.request()
    popup.close()

    client.answer(Reply(True, {"status": 200, "data": 1}))  # must not raise

    assert popup.last_reply is None
    assert not popup.sending


def test_the_copy_button_copies_the_whole_reply(context, monkeypatch):
    copied = []
    monkeypatch.setattr(dpg, "set_clipboard_text", copied.append)
    client = FakeClient()
    popup = popup_for(make_path(), client)
    popup.request()
    client.answer(Reply(True, {"status": 200, "data": {"k": "x" * 200}}))

    popup._copy()

    assert "x" * 200 in copied[0]


# ---------------------------------------------------------------------------
# The requests themselves
# ---------------------------------------------------------------------------


class Answer:
    def __init__(self, status, body):
        self.status_code = status
        self.ok = status < 400
        self._body = body
        self.text = str(body)

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body


def fetch(monkeypatch, answer):
    """Send a request, with the given answer to it, and return the reply."""

    def get(url, params=None, timeout=None):
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(requests, "get", get)
    return APIClient._request("http://x/y", {"a": 1}, 5.0)


def join_requests():
    for thread in threading.enumerate():
        if thread.name.startswith("GET /"):
            thread.join(5)


def test_an_answer_is_a_reply_with_its_data(monkeypatch):
    reply = fetch(monkeypatch, Answer(200, {"status": 200, "data": 3}))

    assert reply.ok
    assert reply.data == {"status": 200, "data": 3}
    assert reply.status_code == 200
    assert reply.error is None


def test_a_bad_input_says_which_one(monkeypatch):
    body = {
        "detail": [
            {"loc": ["query", "kelvin"], "msg": "Field required"},
            {"loc": ["query", "rate"], "msg": "Input should be a valid number"},
        ]
    }

    reply = fetch(monkeypatch, Answer(422, body))

    assert not reply.ok
    assert reply.error == "kelvin: Field required\nrate: Input should be a valid number"


def test_a_message_from_the_server_is_passed_on():
    assert describe_error(400, {"detail": "Queue is empty"}) == "Queue is empty"


def test_a_server_error_that_is_not_json_is_explained(monkeypatch):
    reply = fetch(monkeypatch, Answer(500, "Internal Server Error"))

    assert not reply.ok
    assert "HTTP 500" in reply.error


def test_no_answer_and_no_server_are_explained(monkeypatch):
    assert "No answer after 5 s" in fetch(monkeypatch, requests.Timeout()).error
    assert "Could not reach" in fetch(monkeypatch, requests.ConnectionError()).error
    assert fetch(monkeypatch, RuntimeError("boom")).error == "boom"


def test_the_reply_is_handed_over_on_the_thread_that_dispatches(monkeypatch):
    monkeypatch.setattr(
        requests, "get", lambda url, params=None, timeout=None: Answer(200, {"data": 1})
    )
    client = APIClient()
    received = []

    client.get_async(
        "/x", lambda reply: received.append((reply, threading.current_thread()))
    )
    join_requests()

    assert received == []  # nothing is called until the GUI dispatches
    client.dispatch()
    ((reply, thread),) = received
    assert reply.ok
    assert thread is threading.current_thread()


def test_a_failing_callback_does_not_stop_the_others(monkeypatch):
    monkeypatch.setattr(
        requests, "get", lambda url, params=None, timeout=None: Answer(200, {})
    )
    client = APIClient()
    seen = []

    def bad(reply):
        raise RuntimeError("bad")

    client.get_async("/x", bad)
    join_requests()
    client.get_async("/y", seen.append)
    join_requests()
    client.dispatch()

    assert len(seen) == 1


def test_the_gui_can_be_pickled_to_be_sent_to_its_process():
    """
    The Gui is pickled to start the GUI process, so the client that it holds may not
    hold a queue or a lock until the GUI has started. Running an experiment with its
    GUI failed with `cannot pickle '_thread.lock' object` when it did.
    """
    import pickle

    from pyacquisition.gui import Gui

    gui = pickle.loads(pickle.dumps(Gui()))

    gui.api_client.dispatch()  # nothing has been sent, and it is not a problem


def test_requests_still_work_in_the_process_that_the_gui_was_sent_to(monkeypatch):
    import pickle

    monkeypatch.setattr(
        requests, "get", lambda url, params=None, timeout=None: Answer(200, {"data": 1})
    )
    client = pickle.loads(pickle.dumps(APIClient()))
    seen = []

    client.get_async("/x", seen.append)
    join_requests()
    client.dispatch()

    assert [reply.ok for reply in seen] == [True]
