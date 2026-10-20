import codecs
import csv
import json
import os
import re
import time
from pathlib import Path

from ...core.instrument import SoftwareInstrument, mark_query
from ...core.logging import logger

NAN = float("nan")

# A number as instruments and most programs write one: a sign, digits, a decimal
# point and an exponent. Not a comma as the decimal point, thousands separators,
# nan, inf or hex.
NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


class _NotFound(Exception):
    """The file has no such number now: a passing state of the file, which a
    query rides out with the last number it read."""


def _first_line(text: str) -> str:
    lines = text.splitlines()
    return lines[0] if lines else ""


def _last(matches):
    last = None
    for last in matches:
        pass
    return last


def _delimiter(header: str) -> str:
    """Whichever of tab, semicolon and comma appears most in a CSV's header, or
    a comma if none does."""
    return max("\t;,", key=header.count) if any(d in header for d in "\t;,") else ","


def _cells(line: str, delimiter: str) -> list[str]:
    """A CSV line's cells. A quote may follow the space after a delimiter."""
    return next(csv.reader([line], delimiter=delimiter, skipinitialspace=True), [])


def _is_index(part: str, length: int) -> bool:
    """Whether `part` is a whole number that picks from a list this long."""
    try:
        index = int(part)
    except ValueError:
        return False
    return -length <= index < length


class TextFile(SoftwareInstrument):
    """Reads numbers from a text file that other software writes, such as the
    field that a magnet's own software writes for other programs to read.

    Each query picks a number out of the file in its own way, so each can be
    a measurement, and several measurements can read several numbers from one
    file:

    - `get_first_number` and `get_last_number` read the first or the last
      number in the file. A file that holds only a number is read with either.
    - `get_number_after` reads the number after a label, such as `Field:`, on
      the same line.
    - `get_json_number` reads a value from a JSON file, by its key.
    - `get_csv_number` reads a column of the last row of a CSV file, by the
      column's name.
    - `get_number_by_regex` reads the match of a regular expression, for
      anything else.

    `get_text` gives the whole file, and `get_age` how long ago it changed, to
    check it from the Instruments tab. `get_age` can be a measurement too, to
    record whether the file is being kept up to date.

    A number is written as Python writes one: `-1.5`, `2e-3`, `.5`. A comma as
    the decimal point, thousands separators, `nan` and `inf` aren't read. The
    parts of a date and a time are numbers too: `2026-10-20 14:30` holds
    `2026`, `-10`, `-20`, `14` and `30`. In a file with a timestamp, use a label
    or a regular expression.

    When the file can't be read, or has no such number, as while it is being
    rewritten, a query gives the last number it read instead, or NaN before it
    has read one. The log says so once, as a warning, and again when the file
    reads. A mistake in a query's input, such as an empty label, is an error
    each time.

    The file is read whole each time a query runs, so it suits a small file
    that is rewritten, not a log that grows for days. A file on a network share
    that stops answering holds up the measurements until it answers, as an
    instrument that doesn't reply does.

    The file's encoding is found by itself: UTF-8, with or without a
    byte-order mark, or UTF-16, which Windows PowerShell 5.1 writes. In any
    other encoding, such as `cp1252`, the bytes that aren't UTF-8 are passed
    over, which is enough for the numbers. Give `encoding` to read the rest of
    the text as it is meant.

    In a config file, its `path` goes in the instrument's `args`, as
    [the config file](../config_file.md#instruments) shows.

    Example:
        A magnet's field, from a file that holds only the field:

        ```python
        magnet_file = TextFile("magnet_file", path=r"\\\\lab-server\\magnet\\field.txt")
        self.add_instrument(magnet_file)
        self.add_measurement(Measurement("B", magnet_file.get_first_number, unit="T"))
        ```

        The field and the rate from a JSON file,
        `{"magnet": {"field": 1.25, "rate": 0.1}}`:

        ```python
        magnet = TextFile("magnet", path="C:/magnet/state.json")
        self.add_instrument(magnet)
        self.add_measurement(Measurement("B", magnet.get_json_number, key="magnet.field", unit="T"))
        self.add_measurement(Measurement("rate", magnet.get_json_number, key="magnet.rate"))
        ```

        The newest pressure from a log that another program appends rows to,
        with a header such as `time,pressure,flow`:

        ```python
        gauge = TextFile("gauge", path="C:/gauge/log.csv")
        self.add_instrument(gauge)
        self.add_measurement(Measurement("p", gauge.get_csv_number, column="pressure", unit="mbar"))
        ```

    Args:
        uid: The instrument's id.
        path: The file's path. A `Path` works too.
        encoding: The file's encoding, to override the one found, such as
            `"cp1252"`.
    """

    name = "Text File"

    def __init__(self, uid: str, path: str, encoding: str | None = None):
        super().__init__(uid)
        if encoding is not None:
            try:
                codecs.lookup(encoding)
            except LookupError:
                raise ValueError(f"Unknown encoding: {encoding!r}.") from None
        self._path = Path(os.fspath(path))
        self._encoding = encoding
        # The last number each query gave, by the query and its input, and the
        # queries that can't read the file now (each warned of once).
        self._last = {}
        self._failing = set()

    @property
    def path(self) -> Path:
        """The file's path."""
        return self._path

    @property
    def encoding(self) -> str | None:
        """The encoding given, or None if it is found by itself."""
        return self._encoding

    def _read(self) -> str:
        """The whole file, decoded as the class's docstring says."""
        data = self._path.read_bytes()
        if self._encoding is not None:
            text = data.decode(self._encoding, errors="replace")
        elif data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
            text = data.decode("utf-16", errors="replace")
        elif b"\x00" in data:
            # UTF-16 without a byte-order mark: text has no NUL bytes otherwise,
            # and as UTF-8 its "1.5" would read as 1 (each digit apart).
            order = "be" if data[:1] == b"\x00" else "le"
            text = data.decode(f"utf-16-{order}", errors="replace")
        else:
            text = data.decode("utf-8", errors="replace")
        return text.removeprefix("\ufeff")

    def _number(self, query: str, find) -> float:
        """What `find` gives from the file's text, kept as `query`'s last number.
        If the file can't be read, or `find` finds nothing, the last number
        instead, or NaN before there is one."""
        try:
            number = find(self._read())
        except (OSError, _NotFound) as e:
            reason = (e.strerror if isinstance(e, OSError) else None) or str(e)
            if query not in self._failing:
                self._failing.add(query)
                logger.warning(
                    f"Text file '{self._uid}': {query} can't read {self._path}: "
                    f"{reason}. It gives its last number until it can."
                )
            return self._last.get(query, NAN)
        if query in self._failing:
            self._failing.discard(query)
            logger.info(f"Text file '{self._uid}': {query} reads {self._path} again.")
        self._last[query] = number
        return number

    @mark_query
    def get_first_number(self) -> float:
        """
        Reads the first number in the file. A file that holds only a number is
        read with this.

        Returns:
            float: The number, or the last one read if there is none now.
        """

        def find(text: str) -> float:
            match = NUMBER.search(text)
            if match is None:
                raise _NotFound("it has no number")
            return float(match.group())

        return self._number("get_first_number()", find)

    @mark_query
    def get_last_number(self) -> float:
        """
        Reads the last number in the file, the newest in a file that is
        appended to.

        Returns:
            float: The number, or the last one read if there is none now.
        """

        def find(text: str) -> float:
            match = _last(NUMBER.finditer(text))
            if match is None:
                raise _NotFound("it has no number")
            return float(match.group())

        return self._number("get_last_number()", find)

    @mark_query
    def get_number_after(self, label: str) -> float:
        """
        Reads the number after a label, such as `Field:` in `Field: 1.25 T`. It
        is the first number after the label on the same line, and the label is
        the last one in the file, the newest in a file that is appended to.
        Capitals count.

        Args:
            label (str): The text just before the number. Must not be empty.

        Returns:
            float: The number, or the last one read if there is none now.
        """
        if not label:
            raise ValueError("label must not be empty.")

        def find(text: str) -> float:
            at = text.rfind(label)
            if at < 0:
                raise _NotFound(f"it has no {label!r}")
            match = NUMBER.search(_first_line(text[at + len(label):]))
            if match is None:
                raise _NotFound(f"{label!r} has no number after it on its line")
            return float(match.group())

        return self._number(f"get_number_after({label!r})", find)

    @mark_query
    def get_number_by_regex(self, pattern: str) -> float:
        """
        Reads the last match of a regular expression (Python's `re`), for a
        file the other queries can't read. The number is the pattern's first
        group, or the whole match if it has none: `Field = (\\S+) T`. `^` and
        `$` match at the start and end of each line.

        Args:
            pattern (str): The regular expression. Must not be empty.

        Returns:
            float: The number, or the last one read if there is none now.
        """
        if not pattern:
            raise ValueError("pattern must not be empty.")
        try:
            compiled = re.compile(pattern, re.MULTILINE)
        except re.error as e:
            raise ValueError(f"pattern isn't a regular expression: {e}.") from None

        def find(text: str) -> float:
            match = _last(compiled.finditer(text))
            if match is None:
                raise _NotFound("the pattern matches nothing in it")
            found = match.group(1) if compiled.groups else match.group()
            try:
                return float(found)
            except (TypeError, ValueError):
                raise _NotFound(f"its match {found!r} isn't a number") from None

        return self._number(f"get_number_by_regex({pattern!r})", find)

    @mark_query
    def get_json_number(self, key: str) -> float:
        """
        Reads a number from a JSON file, by its key. Dots go into the document:
        `magnet.field` in `{"magnet": {"field": 1.25}}`. A whole number picks
        from a list, from its end if negative: `readings.-1.value` is the last
        reading's `value`. The value may be a number, or text that reads as one
        (`"1.25"`).

        Args:
            key (str): The value's key, with a dot between its parts. Must not
                be empty.

        Returns:
            float: The number, or the last one read if there is none now.
        """
        if not key:
            raise ValueError("key must not be empty.")
        parts = key.split(".")
        if not all(parts):
            raise ValueError(f"key {key!r} has an empty part.")

        def find(text: str) -> float:
            try:
                value = json.loads(text)
            except ValueError as e:
                raise _NotFound(f"it isn't JSON ({e})") from None
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif isinstance(value, list) and _is_index(part, len(value)):
                    value = value[int(part)]
                else:
                    raise _NotFound(f"it has no {key!r}")
            if isinstance(value, (int, float, str)) and not isinstance(value, bool):
                try:
                    return float(value)
                except ValueError:
                    pass
            raise _NotFound(f"its {key!r} isn't a number")

        return self._number(f"get_json_number({key!r})", find)

    @mark_query
    def get_csv_number(self, column: str) -> float:
        """
        Reads a number from a CSV file: the named column's in the last row.
        The column is named in the header, the first line. Commas, tabs or
        semicolons between the columns are found by themselves. A row is read
        once it ends with a new line, so a row still being written is passed
        over for the one before it.

        Args:
            column (str): The column's name in the header. Must not be empty.

        Returns:
            float: The number, or the last one read if there is none now.
        """
        name = column.strip()
        if not name:
            raise ValueError("column must not be empty.")

        def find(text: str) -> float:
            lines = [line for line in text.splitlines(keepends=True) if line.strip()]
            if not lines:
                raise _NotFound("it is empty")
            header, rows = lines[0], lines[1:]
            names = [cell.strip() for cell in _cells(header, _delimiter(header))]
            if name not in names:
                raise _NotFound(f"its header has no {name!r}")
            complete = [row for row in rows if row.endswith(("\n", "\r"))]
            if not complete:
                raise _NotFound("it has no complete row yet")
            cells = _cells(complete[-1], _delimiter(header))
            at = names.index(name)
            cell = cells[at] if at < len(cells) else ""
            try:
                return float(cell)
            except ValueError:
                raise _NotFound(f"its last row's {name!r} isn't a number ({cell!r})") from None

        return self._number(f"get_csv_number({name!r})", find)

    @mark_query
    def get_text(self) -> str:
        """
        Reads the whole file, to see what the other queries read.

        Returns:
            str: The file's text.

        Raises:
            OSError: If the file can't be read.
        """
        return self._read()

    @mark_query
    def get_age(self) -> float:
        """
        How long ago the file last changed, in seconds. A share whose clock
        differs from this PC's shifts it.

        Returns:
            float: The seconds since it changed, or NaN if it can't be found.
        """
        try:
            return time.time() - self._path.stat().st_mtime
        except OSError:
            return NAN
