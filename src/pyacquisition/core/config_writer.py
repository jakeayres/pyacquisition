"""Writing an experiment's TOML config, keeping what a person wrote in it.

The setup page (`pyacquisition new`) edits a config as a plain dict, in the shape
`tomllib` reads, and `write` changes the file to match it:

- What stays keeps its comments, layout and place. A value that changes keeps
  the comment on its line.
- What is new goes at the end of its section.
- What is removed goes with the comments written above it, and what is moved
  (the measurements' order is the data file's) takes them along.
- A file that doesn't exist yet gets a short header.

The result is read back with `tomllib`, and must give the config, keys in the
same order, or nothing is written.

It uses `tomlkit`, which keeps a file's comments and layout as it parses it.
tomlkit keeps a comment written above a table at the end of whatever came
before it, so this finds each entry's comments itself, and moves whole entries
with its containers' internals (`_set_body`). The tests of this module check
that they still behave.
"""

import tomllib
from pathlib import Path

import tomlkit
from tomlkit.container import Container
from tomlkit.items import Comment, InlineTable, Item, Null, Table, Whitespace

HEADER = (
    "An experiment's config, made with `pyacquisition new`. Run it with",
    "`pyacquisition run --toml <this file>`. See pyacquisition.readthedocs.io",
    "for what each part does.",
)

# The sections whose entries are tables of their own when new ones are added,
# `[measurements.x]` rather than `x = {...}`, unless the file writes them inline.
ENTRY_SECTIONS = ("instruments", "measurements", "calculations")


class ConfigWriteError(ValueError):
    """The config can't be written as it is: it wouldn't read back the same."""


def render(config: dict, text: str | None = None) -> str:
    """The text of a config file holding `config`, changed from `text` (the
    file as it is), or a new file if `text` is None.

    Raises:
        ConfigWriteError: If the result wouldn't read back as `config`.
    """
    if text is not None and _reads_as(text, config):
        return text  # nothing to change, so nothing is
    if text is None:
        document = _new_document()
    else:
        document = tomlkit.parse(text)
        _normalise(document, text)
    _update(document, config, depth=0)
    result = tomlkit.dumps(document)
    try:
        back = tomllib.loads(result)
    except tomllib.TOMLDecodeError as e:
        raise ConfigWriteError(f"The config would not be valid TOML: {e}") from e
    if not same(back, config):
        raise ConfigWriteError("The config would not read back as it was given.")
    return result


def _reads_as(text: str, config: dict) -> bool:
    try:
        return same(tomllib.loads(text), config)
    except tomllib.TOMLDecodeError:
        return False


def write(path: str | Path, config: dict) -> str:
    """Changes the file at `path` to hold `config`, or makes it, in UTF-8.

    Returns:
        str: The text written.

    Raises:
        ConfigWriteError: If the result wouldn't read back as `config`, in which
            case the file is left as it was.
    """
    path = Path(path)
    text = read_text(path) if path.exists() else None
    result = render(config, text)
    if result != text:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(result)
    return result


def read_text(path: Path) -> str:
    """A file's text, with its line endings as they are."""
    with open(path, encoding="utf-8", newline="") as file:
        return file.read()


def same(a, b) -> bool:
    """Whether two values are equal, with their types and their keys' order."""
    if isinstance(a, dict) and isinstance(b, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def _new_document():
    document = tomlkit.document()
    for line in HEADER:
        document.add(tomlkit.comment(line))
    document.add(tomlkit.nl())
    return document


# ---------------------------------------------------------------- containers
def _container(item) -> Container:
    """The container of a table or inline table, or the document itself."""
    return item if isinstance(item, Container) else item.value


def _is_table(item) -> bool:
    """A table with a header of its own (or a super table), not an inline one."""
    return isinstance(item, Table)


def _is_super(item) -> bool:
    """A table with no header of its own: `[calculations.a]` with no `[calculations]`."""
    return _is_table(item) and item.is_super_table()


def _is_loose(item) -> bool:
    """A comment or blank line, which belongs to no key."""
    return isinstance(item, (Comment, Whitespace))


def _entries(container: Container) -> list:
    """The container's body, without what removing keys has left (Null)."""
    return [(k, v) for k, v in container.body if not isinstance(v, Null)]


def _index(entries: list, key: str) -> int:
    return next(i for i, (k, _) in enumerate(entries) if k is not None and k.key == key)


def _set_body(container: Container, entries: list) -> None:
    """Makes the container hold exactly `entries`, in order.

    It rebuilds tomlkit's own record of where each key is, so it relies on its
    internals (`_map`, `_body`, `_raw_append` and the rest).
    """
    container._map.clear()
    container._body.clear()
    container._table_keys.clear()
    container._validation_cache.clear()
    container._out_of_order_keys.clear()
    dict.clear(container)
    for key, item in entries:
        container._raw_append(key, item)


def _without(entries: list, run: list) -> list:
    ids = {id(item) for _, item in run}
    return [entry for entry in entries if id(entry[1]) not in ids]


def _tail_container(item) -> Container:
    """The container whose end is the end of a table in the text: its own, or,
    if it ends with a table of its own, that one's, and so on."""
    container = _container(item)
    while True:
        entries = _entries(container)
        if not entries or entries[-1][0] is None or not _is_table(entries[-1][1]):
            return container
        container = _container(entries[-1][1])


def _leading_run(entries: list, index: int) -> list:
    """The comment lines right above the entry at `index`, with no blank line
    between: those are the entry's. A comment with a blank line after it, such
    as a file's header, belongs to no entry, and stays."""
    start = index
    while start > 0 and entries[start - 1][0] is None and isinstance(entries[start - 1][1], Comment):
        start -= 1
    return entries[start:index]


def _trailing_comments(container: Container) -> list:
    """The comments at the end of a container (see `_leading_run`)."""
    entries = _entries(container)
    return _leading_run(entries, len(entries))


def _detach_trailing_comments(item) -> list:
    """Takes the comments off the end of a table (its tail), and returns them."""
    tail = _tail_container(item)
    run = _trailing_comments(tail)
    if run:
        _set_body(tail, _without(_entries(tail), run))
    return run


def _ends_blank(item) -> bool:
    """Whether a table's text ends with a blank line."""
    entries = _entries(_tail_container(item))
    return bool(entries) and isinstance(entries[-1][1], Whitespace) and "\n" in entries[-1][1].s


def _append_to_tail(item, run: list) -> None:
    """Adds comments (or a blank line) to the end of a table's text."""
    tail = _tail_container(item)
    _set_body(tail, _entries(tail) + run)


# ---------------------------------------------------------------- normalising
def _normalise(document, text: str) -> None:
    """Moves each comment written above a table to just before it, in the
    container that holds the table.

    tomlkit keeps such a comment at the end of whatever came before (the table
    above, or a table in the section above), so removing or moving the table
    would leave it behind. Moved, it is in the same place in the text, which is
    checked: if the text would change, nothing is moved.

    A super table's children are left as they are: a comment in a super table
    gives it a header. `_rearrange_super` finds their comments itself.

    First, a table written in parts (`[instruments.x]` again at the end of the
    file, after other tables, which TOML allows) is gathered into its first
    part: its entries can't otherwise be changed as one. That moves those parts
    in the text, with their comments, so it is left undone unless something in
    the file changes (see `render`).
    """
    if tomlkit.dumps(document) != text:
        return  # tomlkit doesn't give the text back as it was: leave it be
    _gather(document)
    expected = tomlkit.dumps(document)
    snapshot = _snapshot(document)
    try:
        _hoist(document)
    except Exception:  # noqa: BLE001 - a layout this doesn't expect: leave it be
        _restore(snapshot)
        return
    if tomlkit.dumps(document) != expected:
        _restore(snapshot)


def _gather(container: Container) -> None:
    """Joins each table written in parts into its first part: the later parts'
    values before the first part's own tables, and their tables at its end, each
    with the comments written above it."""
    result, first, changed = [], {}, False
    for key, item in _entries(container):
        name = key.key if key is not None else None
        if name in first and _is_table(item) and _is_table(first[name]):
            run = _leading_run(result + [(key, item)], len(result))
            result = result[: len(result) - len(run)]
            if not run and result and result[-1][0] is not None and _is_table(result[-1][1]):
                # Its comments are at the end of the table before it.
                run = _detach_trailing_comments(result[-1][1])
            _join(first[name], item, run)
            changed = True
            continue
        if name is not None and name not in first:
            first[name] = item
        result.append((key, item))
    if changed:
        _set_body(container, result)
    for key, item in _entries(container):
        if _is_table(item):
            _gather(_container(item))


def _join(target: Table, part: Table, run: list) -> None:
    """Adds a later part of a table to its first part. If the first part ended
    with a blank line, before the next section, it still does."""
    ended_blank = _ends_blank(target)
    inner = _container(target)
    entries = _entries(inner)
    parts = _entries(_container(part))
    split = next((i for i, (k, v) in enumerate(parts) if k is not None and _is_table(v)), len(parts))
    values, tables = parts[:split], parts[split:]
    at = next((i for i, (k, v) in enumerate(entries) if k is not None and _is_table(v)), len(entries))
    entries = entries[:at] + values + entries[at:]
    if tables:
        _set_body(inner, entries)
        if not _ends_blank(target):
            _append_to_tail(target, [(None, Whitespace("\n"))])
        entries = _entries(inner) + run + tables
    _set_body(inner, entries)
    if ended_blank and not _ends_blank(target):
        _append_to_tail(target, [(None, Whitespace("\n"))])


def _snapshot(document) -> list:
    """Every container's entries, so that `_hoist` can be undone."""
    saved = []

    def visit(container):
        saved.append((container, _entries(container)))
        for _, item in _entries(container):
            if isinstance(item, (Table, InlineTable)):
                visit(_container(item))

    visit(document)
    return saved


def _restore(snapshot: list) -> None:
    for container, entries in snapshot:
        _set_body(container, entries)


def _hoist(container: Container, is_super: bool = False) -> None:
    if not is_super:
        result, previous, changed = [], None, False
        for key, item in _entries(container):
            if key is not None and _is_table(item) and previous is not None:
                run = _detach_trailing_comments(previous)
                result.extend(run)
                changed = changed or bool(run)
            result.append((key, item))
            if key is not None:
                previous = item if _is_table(item) else None
        if changed:
            _set_body(container, result)
    for key, item in _entries(container):
        if _is_table(item):
            _hoist(_container(item), _is_super(item))


# ---------------------------------------------------------------- changing
def _update(container, wanted: dict, depth: int, section=None, outer=None) -> None:
    """Changes a table (or the document) to hold `wanted`: values in place, then
    entries removed, added or moved, taking their comments. `outer` is the
    container and key of a super table, which holds its first child's comments."""
    item = container
    container = _container(container)
    current = {k.key: v for k, v in _entries(container) if k is not None}

    for key, value in wanted.items():
        if key not in current:
            continue
        existing = current[key]
        if isinstance(value, dict) and isinstance(existing, (Table, InlineTable)):
            _update(
                existing,
                value,
                depth + 1,
                section or key,
                outer=(container, key) if _is_super(existing) else None,
            )
        elif not same(existing.unwrap() if isinstance(existing, Item) else existing, value):
            container[key] = value  # keeps the comment on its line

    if [k for k in current if k in wanted] == list(wanted) and len(current) == len(wanted):
        return
    if outer is not None and _is_super(item):
        _rearrange_super(container, wanted, depth, section, outer)
    else:
        _rearrange(container, wanted, depth, section, inline=isinstance(item, InlineTable))


def _chunks(container: Container):
    """The container's entries in pieces: what comes before its first key, each
    key with the comments above it and the blank lines after it (up to the next
    key's comments), and what comes after its last key, which stays at the end:
    the blank line before the next section, and any comments of its own."""
    entries = _entries(container)
    keyed = [i for i, (k, _) in enumerate(entries) if k is not None]
    if not keyed:
        return entries, {}, []
    starts = [i - len(_leading_run(entries, i)) for i in keyed]
    end = keyed[-1] + 1
    chunks = {}
    for n, index in enumerate(keyed):
        stop = starts[n + 1] if n + 1 < len(keyed) else end
        chunks[entries[index][0].key] = entries[starts[n] : stop]
    return entries[: starts[0]], chunks, entries[end:]


def _item_of(chunk: list):
    return next(item for key, item in chunk if key is not None)


def _rearrange(container: Container, wanted: dict, depth: int, section, inline=False) -> None:
    head, chunks, tail = _chunks(container)
    style = _style(depth, section, [_item_of(c) for c in chunks.values()])
    last_blank = _last_ends_blank([_item_of(c) for c in chunks.values()])

    ordered, seen_table = [], False
    for key, value in wanted.items():
        if key in chunks:
            chunk = chunks[key]
        else:
            new = _new_item(value, style, depth)
            if inline:
                new.trivia.indent = " "  # after the comma, as `{a = 1, b = 2}`
            chunk = [(tomlkit.key(key), new)]
        item = _item_of(chunk)
        if _is_table(item):
            seen_table = True
        elif seen_table:
            # A value after a table would belong to that table in TOML, so one
            # that must come after a table becomes a table itself.
            chunk = [(k, _table(value) if k is not None else i) for k, i in chunk]
        ordered.append(chunk)

    entries = list(head)
    for chunk in ordered:
        if _is_table(_item_of(chunk)) and entries and not _blank_before(entries):
            entries.append((None, Whitespace("\n")))
        entries.extend(chunk)
    _keep_last_blank(last_blank, [_item_of(chunk) for chunk in ordered])
    _set_body(container, entries + tail)


def _last_ends_blank(items: list) -> bool:
    """Whether the last of some entries is a table whose text ends with a blank
    line, which separates it from what follows."""
    return bool(items) and _is_table(items[-1]) and _ends_blank(items[-1])


def _keep_last_blank(was_blank: bool, items: list) -> None:
    """Gives the entry that is last now the blank line the last one had."""
    if was_blank and items and _is_table(items[-1]) and not _ends_blank(items[-1]):
        _append_to_tail(items[-1], [(None, Whitespace("\n"))])


def _blank_before(entries: list) -> bool:
    """Whether the text so far ends with a blank line, for a table to follow."""
    key, item = entries[-1]
    if isinstance(item, Whitespace):
        return "\n" in item.s
    return _is_table(item) and _ends_blank(item)


def _rearrange_super(container: Container, wanted: dict, depth: int, section, outer) -> None:
    """As `_rearrange`, for a super table, which holds only tables: the comments
    above its first table are just before it in its parent, and those above
    each other table are at the end of the table before."""
    parent, parent_key = outer
    above = _entries(parent)
    first_run = _leading_run(above, _index(above, parent_key))
    _set_body(parent, _without(above, first_run))

    keyed = [(k, v) for k, v in _entries(container) if k is not None]
    last_blank = _last_ends_blank([item for _, item in keyed])
    runs, previous = {}, None
    for key, item in keyed:
        runs[key.key] = first_run if previous is None else _detach_trailing_comments(previous)
        previous = item
    existing = {key.key: (key, item) for key, item in keyed}

    ordered = [
        existing.get(key) or (tomlkit.key(key), _new_item(value, "table", depth))
        for key, value in wanted.items()
    ]
    for n, (key, item) in enumerate(ordered):
        run = runs.get(key.key, [])
        if n == 0:
            above = _entries(parent)
            index = _index(above, parent_key)
            _set_body(parent, above[:index] + run + above[index:])
        else:
            before = ordered[n - 1][1]
            if not _ends_blank(before):
                _append_to_tail(before, [(None, Whitespace("\n"))])
            _append_to_tail(before, run)
    _keep_last_blank(last_blank, [item for _, item in ordered])
    _set_body(container, ordered)


# ---------------------------------------------------------------- new entries
def _style(depth: int, section, siblings: list) -> str:
    """How a new dict is written here: "table" ([a.b]) or "inline" ({...})."""
    if depth == 0:
        return "table"
    if depth >= 2:
        return "inline"
    dicts = [s for s in siblings if isinstance(s, (Table, InlineTable))]
    if dicts:
        return "table" if any(_is_table(s) for s in dicts) else "inline"
    return "table" if section in ENTRY_SECTIONS else "inline"


def _new_item(value, style: str, depth: int):
    """A new entry. A new section whose every entry is a table, such as
    `[calculations]`, is written as `[calculations.x]` tables, with no
    `[calculations]` header."""
    if not isinstance(value, dict):
        return tomlkit.item(value)
    if style == "inline":
        return _inline(value)
    entries = depth == 0 and bool(value) and all(isinstance(v, dict) for v in value.values())
    return _table(value, super_table=entries)


def _table(value: dict, super_table: bool = False) -> Table:
    table = tomlkit.table(is_super_table=super_table)
    for key, inner in value.items():
        if isinstance(inner, dict):
            table.add(key, _table(inner) if super_table else _inline(inner))
        else:
            table.add(key, inner)
    return table


def _inline(value: dict) -> InlineTable:
    table = tomlkit.inline_table()
    for key, inner in value.items():
        table.append(key, _inline(inner) if isinstance(inner, dict) else inner)
    return table
