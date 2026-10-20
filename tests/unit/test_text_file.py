"""TextFile: numbers read from a text file that other software writes, each
query picking its own, with the last number given while the file can't be
read (specs/text-file.md)."""

import asyncio
import codecs
import math
import os
import socket
import time

import pandas as pd
import pytest

from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import TextFile
from pyacquisition.instruments.software import text_file


@pytest.fixture
def path(tmp_path):
    return tmp_path / "field.txt"


@pytest.fixture
def logged(monkeypatch):
    """The warnings and info lines the instrument logs, as (level, message)."""
    lines = []
    monkeypatch.setattr(text_file.logger, "warning", lambda m: lines.append(("warning", m)))
    monkeypatch.setattr(text_file.logger, "info", lambda m: lines.append(("info", m)))
    return lines


def reader(path, text=None, **options):
    if text is not None:
        path.write_text(text, encoding="utf-8", newline="")
    return TextFile("file", path=path, **options)


# ------------------------------------------------------------ plain text
@pytest.mark.parametrize("text", ["1.2345", "1.2345\n", "1.2345\r\n"])
def test_a_file_holding_only_a_number_is_read(path, text):
    assert reader(path, text).get_first_number() == 1.2345


@pytest.mark.parametrize(
    "text, number",
    [("-0.5", -0.5), ("-0.5\n", -0.5), ("1.2e-3", 1.2e-3), ("1.2e-3\n", 1.2e-3), ("+7", 7.0)],
)
def test_signs_and_exponents_are_read(path, text, number):
    assert reader(path, text).get_first_number() == number


def test_the_first_and_the_last_number(path):
    file = reader(path, "a -1.5 b\n+2e3 c .5 d\n")

    assert file.get_first_number() == -1.5
    assert file.get_last_number() == 0.5


def test_a_number_after_a_label_anywhere_on_its_line(path):
    file = reader(path, "Field: 1.5 T\nMagnet Temperature: 4.2 K ok\nRate:0.1\n")

    assert file.get_number_after("Field:") == 1.5
    assert file.get_number_after("Temperature:") == 4.2
    assert file.get_number_after("Rate:") == 0.1


def test_a_label_without_a_number_on_its_line_doesnt_take_the_next_lines(path):
    file = reader(path, "Field: --\nRate: 0.1\nTarget:\n2.0\n")

    assert math.isnan(file.get_number_after("Field:"))
    assert math.isnan(file.get_number_after("Target:"))


def test_the_last_label_in_the_file_is_read(path):
    file = reader(path, "Field: 1\nField: 2\n")

    assert file.get_number_after("Field:") == 2


def test_a_label_matches_capitals_as_written(path):
    file = reader(path, "field: 1\nFIELD: 2\n")

    assert file.get_number_after("field:") == 1


def test_a_regex_with_a_group_takes_the_group(path):
    file = reader(path, "Field = 1.5 T (set 2.0 T)\n")

    assert file.get_number_by_regex(r"Field = (\S+) T") == 1.5


def test_a_regex_without_a_group_takes_the_whole_match(path):
    file = reader(path, "set 2.0 T, now 1.5 T\n")

    assert file.get_number_by_regex(r"\d+\.\d+(?= T)") == 1.5  # the last match


def test_a_regex_caret_matches_at_each_lines_start(path):
    file = reader(path, "B: 1\nAB: 5\n")

    assert file.get_number_by_regex(r"^B: (\S+)") == 1


def test_a_regex_match_that_isnt_a_number_is_no_number(path):
    file = reader(path, "Field = high\n")

    assert math.isnan(file.get_number_by_regex(r"Field = (\S+)"))


def test_the_whole_text_and_the_age(path):
    file = reader(path, "Field: 1.5\n")
    os.utime(path, (time.time() - 100, time.time() - 100))

    assert file.get_text() == "Field: 1.5\n"
    assert 99 < file.get_age() < 110


# ------------------------------------------------------------ encodings
def test_utf8_with_a_byte_order_mark(path):
    path.write_bytes(codecs.BOM_UTF8 + b"Field: 1.5")

    assert TextFile("file", path).get_first_number() == 1.5
    assert TextFile("file", path).get_text() == "Field: 1.5"


def test_utf16_with_a_byte_order_mark_as_powershell_writes_it(path):
    path.write_bytes("Field: 1.5\r\n".encode("utf-16"))

    assert TextFile("file", path).get_number_after("Field:") == 1.5


def test_bytes_that_arent_utf8_dont_stop_the_numbers(path):
    path.write_bytes("T = 4.2\xb0C\n".encode("cp1252"))

    assert TextFile("file", path).get_number_after("T =") == 4.2


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be"])
def test_utf16_without_a_byte_order_mark(path, encoding):
    path.write_bytes("Field: 1.5\r\n".encode(encoding))

    assert TextFile("file", path).get_number_after("Field:") == 1.5


def test_an_encoding_given_wins(path):
    path.write_bytes(b"T = 4.2\xb0C")  # cp1252's degree sign

    assert TextFile("file", path, encoding="cp1252").get_text() == "T = 4.2\u00b0C"
    assert TextFile("file", path).get_text() == "T = 4.2\ufffdC"


def test_an_unknown_encoding_is_refused_when_it_is_made(path):
    with pytest.raises(ValueError, match="Unknown encoding"):
        TextFile("file", path, encoding="nonsense")


# ------------------------------------------------------------ failure
def test_making_one_reads_nothing(path):
    TextFile("file", path)  # the file doesn't exist


def test_a_missing_file_gives_nan_then_the_last_number(path):
    file = TextFile("file", path)

    assert math.isnan(file.get_first_number())
    path.write_text("1.5", encoding="utf-8")
    assert file.get_first_number() == 1.5
    path.unlink()
    assert file.get_first_number() == 1.5


@pytest.mark.parametrize("text", ["", "no numbers here"])
def test_an_empty_file_or_no_number_gives_the_last_number(path, text):
    file = reader(path, "Field: 1.5")
    assert file.get_number_after("Field:") == 1.5

    path.write_text(text, encoding="utf-8")
    assert file.get_number_after("Field:") == 1.5
    assert math.isnan(file.get_first_number())  # it has never read one


def test_each_query_and_input_keeps_its_own_last_number(path):
    file = reader(path, "A: 1\nB: 2\n")
    assert (file.get_number_after("A:"), file.get_number_after("B:")) == (1, 2)

    path.write_text("A: 3\n", encoding="utf-8")
    assert (file.get_number_after("A:"), file.get_number_after("B:")) == (3, 2)


def test_a_run_of_failures_is_logged_once_and_the_recovery_once(path, logged):
    file = TextFile("magnet_file", path)

    for _ in range(3):
        file.get_first_number()
    assert len(logged) == 1
    level, message = logged[0]
    assert level == "warning"
    assert "magnet_file" in message and "get_first_number()" in message and str(path) in message

    path.write_text("1.5", encoding="utf-8")
    file.get_first_number()
    file.get_first_number()
    assert [level for level, _ in logged] == ["warning", "info"]


def test_each_query_and_input_is_warned_of_on_its_own(path, logged):
    file = reader(path, "A: 1\n")

    for _ in range(2):
        file.get_number_after("A:")
        file.get_number_after("B:")
    assert [m for _, m in logged] == [
        f"Text file 'file': get_number_after('B:') can't read {path}: it has no 'B:'. "
        "It gives its last number until it can."
    ]


def test_the_age_of_a_missing_file_is_nan(path):
    assert math.isnan(TextFile("file", path).get_age())


def test_the_text_of_a_missing_file_raises(path):
    with pytest.raises(FileNotFoundError):
        TextFile("file", path).get_text()


# ------------------------------------------------------------ mistakes
def test_an_empty_label_raises_every_time(path):
    file = reader(path, "Field: 1.5")

    for _ in range(2):
        with pytest.raises(ValueError, match="label must not be empty"):
            file.get_number_after("")


@pytest.mark.parametrize("pattern, reason", [("(", "isn't a regular expression"), ("", "must not be empty")])
def test_a_bad_regex_raises_every_time(path, pattern, reason):
    file = reader(path, "Field: 1.5")

    for _ in range(2):
        with pytest.raises(ValueError, match=reason):
            file.get_number_by_regex(pattern)


# ------------------------------------------------------------ JSON
DOCUMENT = '{"field": 1.5, "magnet": {"field": 2.5, "rate": "0.1", "on": true},' \
    ' "readings": [{"value": 1}, {"value": 2}, {"value": 3}]}'


@pytest.mark.parametrize(
    "key, number",
    [
        ("field", 1.5),
        ("magnet.field", 2.5),
        ("readings.0.value", 1),
        ("readings.-1.value", 3),
        ("magnet.rate", 0.1),  # a number as text
    ],
)
def test_a_json_number_by_its_key(path, key, number):
    assert reader(path, DOCUMENT).get_json_number(key) == number


@pytest.mark.parametrize(
    "key, readable",
    [
        ("magnet.on", '{"magnet": {"on": 4}}'),  # true isn't a number
        ("magnet.missing", '{"magnet": {"missing": 4}}'),
        ("readings.9.value", '{"readings": [' + '{"value": 0}, ' * 9 + '{"value": 4}]}'),
        ("readings.x", '{"readings": {"x": 4}}'),
        ("field.more", '{"field": {"more": 4}}'),
    ],
)
def test_a_json_value_that_isnt_a_number_or_isnt_there_gives_the_last_number(path, key, readable):
    file = reader(path, DOCUMENT)
    assert math.isnan(file.get_json_number(key))

    path.write_text(readable, encoding="utf-8")
    assert file.get_json_number(key) == 4
    path.write_text(DOCUMENT, encoding="utf-8")
    assert file.get_json_number(key) == 4


def test_a_json_file_cut_off_mid_write_gives_the_last_number(path):
    file = reader(path, DOCUMENT)
    assert file.get_json_number("magnet.field") == 2.5

    path.write_text(DOCUMENT[:30], encoding="utf-8")
    assert file.get_json_number("magnet.field") == 2.5


def test_a_json_file_with_a_byte_order_mark(path):
    path.write_bytes(codecs.BOM_UTF8 + b'{"field": 1.5}')

    assert TextFile("file", path).get_json_number("field") == 1.5


@pytest.mark.parametrize("key, reason", [("", "must not be empty"), ("magnet..field", "empty part")])
def test_an_empty_json_key_raises_every_time(path, key, reason):
    file = reader(path, DOCUMENT)

    for _ in range(2):
        with pytest.raises(ValueError, match=reason):
            file.get_json_number(key)


# ------------------------------------------------------------ CSV
@pytest.mark.parametrize("delimiter", [",", "\t", ";"])
def test_a_csv_column_in_the_last_row_with_its_delimiter_found(path, delimiter):
    rows = ["time,field,rate", "1,0.5,0.1", "2,0.6,0.1", ""]
    file = reader(path, "\n".join(row.replace(",", delimiter) for row in rows))

    assert file.get_csv_number("field") == 0.6
    assert file.get_csv_number("time") == 2


def test_a_quoted_header_and_spaces_around_names(path):
    file = reader(path, '"time (s)", "field, in T" ,rate\n1, 0.5 ,0.1\n')

    assert file.get_csv_number("field, in T") == 0.5
    assert file.get_csv_number(" time (s) ") == 1


def test_a_row_without_its_new_line_is_passed_over(path):
    file = reader(path, "time,field\n1,0.5\n2,0.6\n3,0.")

    assert file.get_csv_number("field") == 0.6


def test_blank_lines_are_passed_over(path):
    file = reader(path, "\ntime,field\n\n1,0.5\n\n")

    assert file.get_csv_number("field") == 0.5


def test_a_header_with_no_rows_yet_gives_nan(path):
    assert math.isnan(reader(path, "time,field\n").get_csv_number("field"))
    assert math.isnan(reader(path, "time,field\n1,0.").get_csv_number("field"))


@pytest.mark.parametrize("text", ["time,rate\n1,0.1\n", "time,field\n1,\n", "time,field\n1\n", "time,field\n1,high\n"])
def test_a_missing_column_or_cell_gives_the_last_number(path, text):
    file = reader(path, "time,field\n1,0.5\n")
    assert file.get_csv_number("field") == 0.5

    path.write_text(text, encoding="utf-8")
    assert file.get_csv_number("field") == 0.5


def test_an_empty_column_name_raises_every_time(path):
    file = reader(path, "time,field\n1,0.5\n")

    for _ in range(2):
        with pytest.raises(ValueError, match="column must not be empty"):
            file.get_csv_number(" ")


# ------------------------------------------------------------ end to end
def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


class Lab(Experiment):
    file_path = None

    def setup(self):
        magnet_file = TextFile("magnet_file", path=self.file_path)
        self.add_instrument(magnet_file)
        self.add_measurement(Measurement("B", magnet_file.get_first_number, unit="T"))


def test_an_experiment_records_each_new_number_in_the_file(tmp_path, path):
    path.write_text("1.0\n", encoding="utf-8")
    experiment = Lab(
        root_path=str(tmp_path), data_path="data", api_server_port=free_port(),
        measurement_period=0.05, gui=False,
    )
    experiment.file_path = path

    async def rows_after(count):
        end = time.monotonic() + 10
        target = experiment._scribe.rows_written + count
        while experiment._scribe.rows_written < target:
            assert time.monotonic() < end, "no rows were written"
            await asyncio.sleep(0.01)

    async def script():
        await rows_after(3)
        path.write_text("2.0\n", encoding="utf-8")
        await rows_after(3)
        path.write_text("-3.5e-1\n", encoding="utf-8")
        await rows_after(3)

    async def drive():
        try:
            while not experiment._started:
                await asyncio.sleep(0.01)
            await script()
        finally:
            experiment._shutdown_event.set()

    async def both():
        await asyncio.gather(experiment._run(), drive())

    asyncio.run(asyncio.wait_for(both(), timeout=60))

    column = pd.read_csv(tmp_path / "data" / "00.00 start.data")["B"]
    changes = [value for i, value in enumerate(column) if i == 0 or value != column[i - 1]]
    assert changes == [1.0, 2.0, -0.35]
