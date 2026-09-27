"""The palette's search line (palette-line.js): where the search ends and the
arguments begin, and the arguments matched to an item's inputs. The functions
are pure, so they are imported in the page and called there."""

import pytest

pytest.importorskip("playwright")

from ui_helpers import Page

# Inputs as describeField gives them (forms.js).
WAIT = [
    {"name": n, "title": n.title(), "type": "integer", "required": False, "default": 0,
     "choices": None, "labels": None}
    for n in ("hours", "minutes", "seconds")
]
NEW_FILE = [
    {"name": "file_name", "title": "File Name", "type": "text", "required": True,
     "choices": None, "labels": None},
    {"name": "increment_block", "title": "Increment Block", "type": "boolean",
     "required": False, "default": False, "choices": None, "labels": None},
]
OUTPUTS = ["OUTPUT_1", "OUTPUT_2", "OUTPUT_3", "OUTPUT_4"]
# RampTemperature's inputs, with the Lakeshore offered as a choice (as it is when
# the server leaves it to be picked).
RAMP = [
    {"name": "lakeshore", "title": "Lakeshore", "type": "choice", "required": True,
     "choices": ["lakeshore"], "labels": ["lakeshore"]},
    {"name": "output_channel", "title": "Output Channel", "type": "choice", "required": True,
     "choices": OUTPUTS, "labels": [f"Output {i}" for i in range(1, 5)]},
    {"name": "setpoint", "title": "Setpoint", "type": "number", "required": True,
     "choices": None, "labels": None},
    {"name": "ramp_rate", "title": "Ramp Rate", "type": "number", "required": True,
     "choices": None, "labels": None},
]
ITEMS = [
    {"id": "/tasks/waitfor", "label": "WaitFor", "text": "WaitFor Wait for a while task"},
    {"id": "/tasks/waituntil", "label": "WaitUntil", "text": "WaitUntil Wait until a time task"},
    {"id": "/tasks/newfile", "label": "NewFile", "text": "NewFile Start a new file task"},
    {"id": "/tasks/ramp_temperature", "label": "RampTemperature",
     "text": "RampTemperature Ramp temperature setpoint task"},
    {"id": "/clock/read_timer", "label": "clock.read_timer",
     "text": "clock read_timer Read timer Query"},
]


@pytest.fixture(scope="module")
def line(browser, server):
    """Calls a function of palette-line.js in a page: line(name, *args)."""
    context = browser.new_context()
    page = Page(context.new_page())
    page.page.goto(f"{server}/")
    page.page.wait_for_function("document.querySelector('#app')")

    def call(name, *args):
        return page.page.evaluate(
            "async ([name, args]) => (await import('/ui/js/palette-line.js'))[name](...args)",
            [name, list(args)],
        )

    yield call
    assert page.errors == []
    context.close()


def texts(found):
    return [t["text"] for t in found]


# ------------------------------------------------------------ tokens
def test_tokens_split_on_spaces_and_keep_quoted_text_whole(line):
    found = line("tokens", '  new   file "cold run"  \'a b\' x ')

    assert texts(found) == ["new", "file", "cold run", "a b", "x"]
    assert [t["quoted"] for t in found] == [False, False, True, True, False]


def test_a_token_with_an_equals_is_named(line):
    found = line("tokens", 'seconds=30 file_name="cold run" =5 a=b=c "x=1"')

    assert [(t["name"], t["value"]) for t in found] == [
        ("seconds", "30"),
        ("file_name", "cold run"),
        (None, None),  # no name before it
        ("a", "b=c"),
        (None, None),  # quoted: it is text
    ]


def test_an_unclosed_quote_runs_to_the_end(line):
    assert texts(line("tokens", 'new file "cold run')) == ["new", "file", "cold run"]


# ------------------------------------------------------------ where the search ends
def split(line, text, locked=None):
    found = line("splitLine", text, ITEMS, locked)
    return found["search"], texts(found["arguments"]), found["locked"]


def test_the_search_ends_at_a_number_quoted_text_or_a_name(line):
    assert split(line, "wait 0 5") == ("wait", ["0", "5"], False)
    assert split(line, "ramp temp 300 5 output_1") == ("ramp temp", ["300", "5", "output_1"], False)
    assert split(line, "wait seconds=30 0") == ("wait", ["seconds=30", "0"], False)
    assert split(line, 'new file "cold run"') == ("new file", ["cold run"], False)


def test_the_search_ends_at_a_word_that_would_leave_nothing_matching(line):
    assert split(line, "new file cold") == ("new file", ["cold"], False)
    assert split(line, "new file cold run") == ("new file", ["cold", "run"], False)
    assert split(line, "wait for") == ("wait for", [], False)  # still matches WaitFor


def test_a_word_inside_another_is_an_argument(line):
    # "lap" is in "elapsed", but starts no word of the item: it is a timer's name.
    items = [{"id": "/clock/read_timer", "label": "clock.read_timer",
              "text": "clock read_timer Read the time elapsed on a timer Query"}]

    assert split_items(line, "clock read_timer lap", items) == ("clock read_timer", ["lap"], False)
    assert split_items(line, "clock read_timer elap", items) == ("clock read_timer elap", [], False)
    assert split_items(line, "clock timer", items) == ("clock timer", [], False)


def split_items(line, text, items):
    found = line("splitLine", text, items, None)
    return found["search"], texts(found["arguments"]), found["locked"]


def test_a_search_that_matches_nothing_has_no_arguments(line):
    assert split(line, "zzzz yyyy") == ("zzzz yyyy", [], False)
    assert split(line, "") == ("", [], False)


def test_after_tab_everything_past_the_label_is_an_argument(line):
    new_file = ITEMS[2]

    assert split(line, "NewFile cold run", new_file) == ("NewFile", ["cold", "run"], True)
    assert split(line, "newfile wait 5", new_file) == ("NewFile", ["wait", "5"], True)
    # Deleting into the label lets it go.
    assert split(line, "NewFil", new_file) == ("NewFil", [], False)


# ------------------------------------------------------------ matching the arguments
def match(line, fields, text):
    return line("matchArguments", fields, line("tokens", text))


def test_positional_arguments_fill_the_inputs_in_order(line):
    found = match(line, WAIT, "0 5")

    assert found["values"] == {"hours": "0", "minutes": "5", "seconds": "0"}
    assert found["given"] == [["hours", "0"], ["minutes", "5"]]
    assert found["ok"] and found["errors"] == {} and found["problems"] == []


def test_named_arguments_go_first_and_the_rest_fill_around_them(line):
    found = match(line, WAIT, "0 seconds=30")

    assert found["values"] == {"hours": "0", "minutes": "0", "seconds": "30"}
    assert found["given"] == [["seconds", "30"], ["hours", "0"]]
    assert found["ok"]


def test_names_ignore_case(line):
    assert match(line, WAIT, "MINUTES=2")["values"]["minutes"] == "2"


def test_too_many_arguments_is_a_problem_on_the_last_input(line):
    found = match(line, WAIT, "1 2 3 4")

    assert not found["ok"]
    assert found["errors"] == {"seconds": "`4` has nowhere to go: every input is filled."}


def test_a_word_that_nothing_takes_is_a_problem_on_the_next_input(line):
    found = match(line, WAIT, "abc")

    assert not found["ok"]
    assert found["errors"]["hours"].startswith("Nothing left here takes `abc`: `hours` takes a whole number")


def test_an_unknown_name_is_a_problem(line):
    found = match(line, WAIT, "days=3")

    assert found["problems"] == ["No input called `days`. Its inputs are `hours`, `minutes` and `seconds`."]
    assert not found["ok"]


def test_a_name_given_twice_is_a_problem(line):
    found = match(line, WAIT, "hours=1 hours=2")

    assert found["errors"] == {"hours": "`hours` is given twice."}
    assert found["values"]["hours"] == "1"


def test_a_named_value_of_the_wrong_kind_is_a_problem_by_its_input(line):
    found = match(line, WAIT, "hours=soon")

    assert found["errors"] == {"hours": "`soon` isn't a whole number."}
    assert found["values"]["hours"] == "soon"  # as typed, in the form


def test_words_that_nothing_else_takes_join_the_text_before_them(line):
    found = match(line, NEW_FILE, "cold run")

    assert found["values"] == {"file_name": "cold run", "increment_block": False}
    assert found["given"] == [["file_name", "cold run"]]
    assert found["ok"]


def test_a_word_a_later_input_takes_goes_to_it(line):
    found = match(line, NEW_FILE, "cold yes")

    assert found["values"] == {"file_name": "cold", "increment_block": True}


@pytest.mark.parametrize(
    "text, value",
    [("true", True), ("yes", True), ("on", True), ("1", True), ("Off", False), ("no", False), ("0", False)],
)
def test_booleans_are_typed_as_words_or_digits(line, text, value):
    found = match(line, NEW_FILE, f"cold increment_block={text}")

    assert found["values"]["increment_block"] is value


def test_a_boolean_that_isnt_one_is_a_problem(line):
    found = match(line, NEW_FILE, "cold increment_block=maybe")

    assert found["errors"] == {"increment_block": "`maybe` isn't yes or no."}


def test_a_required_input_left_empty_is_a_problem(line):
    found = match(line, NEW_FILE, "increment_block=yes")

    assert found["errors"] == {"file_name": "Required."}  # from checkValues
    assert not found["ok"]


def test_a_one_choice_input_is_filled_and_numbers_pass_over_a_choice(line):
    found = match(line, RAMP, "300 5 output_1")

    assert found["values"] == {
        "lakeshore": "lakeshore",  # its one choice
        "output_channel": "OUTPUT_1",  # by its value, ignoring case
        "setpoint": "300",  # past the channel, which doesn't list 300
        "ramp_rate": "5",
    }
    assert found["ok"]


def test_a_choice_is_found_by_its_label(line):
    found = match(line, RAMP, "setpoint=4 ramp_rate=1 'Output 2'")

    assert found["values"]["output_channel"] == "OUTPUT_2"
    assert found["ok"]


def test_a_choice_that_isnt_one_is_a_problem(line):
    found = match(line, RAMP, "output_channel=OUTPUT_9 300 5")

    assert found["errors"]["output_channel"] == "`OUTPUT_9` isn't one of Output 1, Output 2, Output 3, Output 4."


def test_the_forms_checks_come_through(line):
    found = match(line, RAMP, "300")

    assert found["errors"] == {"output_channel": "Required.", "ramp_rate": "Required."}


@pytest.mark.parametrize(
    "field, text, value",
    [
        ({"type": "number"}, "2e-3", "2e-3"),
        ({"type": "number"}, "-1.5", "-1.5"),
        ({"type": "integer"}, "3", "3"),
        ({"type": "text"}, "any thing", "any thing"),
    ],
)
def test_typed_values(line, field, text, value):
    assert line("typedValue", {"name": "x", **field}, text) == {"value": value}


def test_a_value_an_input_cant_take_says_what_it_takes(line):
    assert line("typedValue", {"name": "x", "type": "integer"}, "1.5") == {"refused": "a whole number"}
