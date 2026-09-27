"""Writing a config (core/config_writer.py): what a person wrote is kept, and
what changes takes its comments with it."""

import tomllib
from pathlib import Path

import pytest

from pyacquisition.core import config_writer
from pyacquisition.core.config_writer import ConfigWriteError, render, same, write

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

RIG = """\
# The cryostat rig.

[rack]
period = 0.5  # fast enough for the lock-in

[instruments]
clock = {instrument = "Clock"}  # for the time column

# The lock-in, on the sample.
[instruments.lockin]
instrument = "SR_830"
adapter = "mock"
resource = "GPIB0::7::INSTR"

[measurements]
# Time first.
t = {instrument = "clock", method = "timestamp_ms"}
# Then the signal.
x = {instrument = "lockin", method = "get_x", unit = "V"}

# Smoothed.
[calculations.x_smooth]
calculation = "RollingMean"
column = "x"
window = 10

# Everything.
[calculations.total]
calculation = "Sum"
inputs = ["t", "x"]
"""


def config(text=RIG) -> dict:
    return tomllib.loads(text)


def changed(**sections) -> dict:
    new = config()
    new.update(sections)
    return new


# ------------------------------------------------------------ what stays
@pytest.mark.parametrize(
    "text",
    [
        RIG,
        RIG.replace("\n", "\r\n"),
        (EXAMPLES / "front_page.toml").read_text(encoding="utf-8"),
        (EXAMPLES / "calculations.toml").read_text(encoding="utf-8"),
    ],
    ids=["rig", "rig with CRLF", "front_page", "calculations"],
)
def test_nothing_changed_keeps_the_file_byte_for_byte(text):
    assert render(config(text), text) == text


def test_changing_a_value_keeps_every_comment():
    new = config()
    new["rack"]["period"] = 0.25

    result = render(new, RIG)

    assert result == RIG.replace("period = 0.5", "period = 0.25")


def test_changing_a_value_in_an_inline_table_keeps_the_rest():
    new = config()
    new["measurements"]["x"]["unit"] = "mV"

    result = render(new, RIG)

    assert result == RIG.replace('unit = "V"', 'unit = "mV"')


# ------------------------------------------------------------ adding
def test_a_new_instrument_goes_at_the_end_of_its_section_as_its_neighbours_are():
    new = config()
    new["instruments"]["lakeshore"] = {
        "instrument": "Lakeshore_350",
        "adapter": "mock",
        "resource": "GPIB0::12::INSTR",
        "args": {"timeout": 2000},
    }

    result = render(new, RIG)

    lockin = 'resource = "GPIB0::7::INSTR"\n\n'
    assert result == RIG.replace(
        lockin,
        lockin
        + "[instruments.lakeshore]\n"
        + 'instrument = "Lakeshore_350"\n'
        + 'adapter = "mock"\n'
        + 'resource = "GPIB0::12::INSTR"\n'
        + "args = {timeout = 2000}\n\n",
    )


def test_a_new_key_in_an_inline_table_is_spaced_as_the_others():
    new = config()
    new["measurements"]["t"]["args"] = {"n": 1}
    new["measurements"]["t"]["unit"] = "ms"

    result = render(new, RIG)

    assert 't = {instrument = "clock", method = "timestamp_ms", args = {n = 1}, unit = "ms"}' in result


def test_a_new_entry_goes_before_the_blank_line_that_ends_its_section():
    new = config()
    new["measurements"]["y"] = {"instrument": "lockin", "method": "get_y"}

    result = render(new, RIG)

    assert result == RIG.replace(
        'unit = "V"}\n',
        'unit = "V"}\ny = {instrument = "lockin", method = "get_y"}\n',
    )


def test_a_new_measurement_among_inline_ones_is_inline():
    new = config()
    new["measurements"]["y"] = {"instrument": "lockin", "method": "get_y"}

    result = render(new, RIG)

    assert 'y = {instrument = "lockin", method = "get_y"}' in result
    assert result.index("x = {") < result.index("y = {") < result.index("[calculations")


def test_a_new_section_goes_at_the_end():
    new = changed(data={"path": "data"})

    result = render(new, RIG)

    assert result.startswith(RIG)
    assert result.endswith('[data]\npath = "data"\n')


# ------------------------------------------------------------ removing
def test_a_removed_instrument_goes_with_its_comments():
    new = config()
    del new["instruments"]["lockin"]
    del new["measurements"]["x"]
    new["calculations"] = {"total": {"calculation": "Sum", "inputs": ["t"]}}

    result = render(new, RIG)

    assert "lockin" not in result
    assert "# The lock-in, on the sample." not in result
    assert "# Then the signal." not in result
    assert "# Smoothed." not in result
    assert "# Everything." in result
    assert "# Time first." in result
    assert "# for the time column" in result


def test_a_removed_section_goes():
    new = config()
    del new["rack"]

    result = render(new, RIG)

    assert "[rack]" not in result and "fast enough" not in result
    assert "# The cryostat rig." in result


# ------------------------------------------------------------ moving
def test_reordered_measurements_take_their_comments():
    new = config()
    new["measurements"] = {"x": new["measurements"]["x"], "t": new["measurements"]["t"]}

    result = render(new, RIG)

    assert list(tomllib.loads(result)["measurements"]) == ["x", "t"]
    assert result.index("# Then the signal.") < result.index("x = {")
    assert result.index("x = {") < result.index("# Time first.") < result.index("t = {")


def test_reordered_calculations_take_their_comments():
    new = config()
    calculations = new["calculations"]
    new["calculations"] = {"total": calculations["total"], "x_smooth": calculations["x_smooth"]}

    result = render(new, RIG)

    assert list(tomllib.loads(result)["calculations"]) == ["total", "x_smooth"]
    assert result.index("# Everything.") < result.index("[calculations.total]")
    assert (
        result.index("[calculations.total]")
        < result.index("# Smoothed.")
        < result.index("[calculations.x_smooth]")
    )
    assert "[calculations]" not in result  # still no header of its own


# ------------------------------------------------------------ a new file
def test_a_new_file_has_a_header_and_reads_back():
    new = config()

    result = render(new)

    assert result.startswith("# An experiment's config, made with `pyacquisition new`.")
    assert same(tomllib.loads(result), new)
    assert "[instruments.clock]" in result  # the entries are tables of their own
    assert "[measurements.x]" in result


def test_write_makes_a_new_file(tmp_path):
    path = tmp_path / "rig.toml"

    write(path, {"rack": {"period": 0.5}})

    assert tomllib.loads(path.read_text(encoding="utf-8")) == {"rack": {"period": 0.5}}


def test_write_changes_a_file_and_keeps_its_line_endings(tmp_path):
    path = tmp_path / "rig.toml"
    path.write_bytes(RIG.replace("\n", "\r\n").encode("utf-8"))
    new = config()
    new["rack"]["period"] = 0.25

    write(path, new)

    assert path.read_bytes() == RIG.replace("period = 0.5", "period = 0.25").replace(
        "\n", "\r\n"
    ).encode("utf-8")


def test_write_keeps_non_ascii_text(tmp_path):
    path = tmp_path / "rig.toml"
    path.write_text("# Température.\n[data]\npath = \"données\"\n", encoding="utf-8")

    write(path, {"data": {"path": "données", "delimiter": ";"}})

    text = path.read_text(encoding="utf-8")
    assert "# Température." in text and 'path = "données"' in text


# ------------------------------------------------------------ refusing
def test_a_result_that_would_not_read_back_writes_nothing(tmp_path, monkeypatch):
    path = tmp_path / "rig.toml"
    path.write_text(RIG, encoding="utf-8")
    monkeypatch.setattr(config_writer.tomlkit, "dumps", lambda document: "[rack]\nperiod = 9\n")
    new = config()
    new["rack"]["period"] = 0.25

    with pytest.raises(ConfigWriteError):
        write(path, new)

    assert path.read_text(encoding="utf-8") == RIG


def test_same_minds_types_and_order():
    assert same({"a": 1, "b": 2}, {"a": 1, "b": 2})
    assert not same({"a": 1, "b": 2}, {"b": 2, "a": 1})
    assert not same({"a": 1}, {"a": 1.0})
    assert not same({"a": True}, {"a": 1})
