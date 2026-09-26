"""What a task's endpoint asks for, so a form can be built from the API schema
alone: each input's type, its default, what it is for, and, where only some
values make sense, the choices.

- The default is the dataclass field's, so an input with one can be left out.
- What it is for comes from the task's docstring, from an `Attributes:` (or
  `Args:`) section in the Google style: `seconds (int): How long to wait.`
- An enum input is asked for as text (see `resolve_enum_kwargs`), and its
  members' names are listed as the choices (`enum` in the schema), with the
  labels an interface shows (`x-labels`). Other spellings are still accepted.
- An input that names an instrument (a task's `applies_to`) lists the ids of the
  experiment's instruments of that kind as its choices.
"""

import re
from dataclasses import MISSING, fields
from enum import Enum
from inspect import Parameter
from typing import Annotated, get_type_hints

from fastapi import Query

from ..instrument import _allows_text, enum_classes

SECTIONS = ("Attributes", "Args", "Arguments", "Parameters")
_SECTION = re.compile(rf"^(\s*)({'|'.join(SECTIONS)}):\s*$")
_ENTRY = re.compile(r"^(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)$")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def attribute_docs(cls) -> dict[str, str]:
    """What each input is for, from the class docstring's `Attributes:` section
    (or `Args:`), by name. An entry starts at the indent of the section's first
    line, and lines indented further carry it on."""
    docs = {}
    lines = (cls.__doc__ or "").expandtabs().splitlines()
    i = 0
    while i < len(lines):
        section = _SECTION.match(lines[i])
        i += 1
        if not section:
            continue
        entry_indent = None
        name = None
        while i < len(lines):
            line = lines[i]
            if line.strip():
                if _indent(line) <= len(section.group(1)):
                    break  # the section has ended
                if entry_indent is None:
                    entry_indent = _indent(line)
                entry = _ENTRY.match(line.strip())
                if _indent(line) == entry_indent and entry:
                    name = entry.group(1)
                    docs[name] = entry.group(2).strip()
                elif name:
                    docs[name] = f"{docs[name]} {line.strip()}".strip()
            i += 1
    return docs


def _enum_choices(enums: list) -> tuple[list, list]:
    """The members' names, and their labels, of one or more enums (members of
    the same name, as in two instruments' copies of an enum, are one choice)."""
    names, labels = [], []
    for enum in enums:
        for member in enum:
            if member.name not in names:
                names.append(member.name)
                label = getattr(member, "label", None)
                labels.append(label if isinstance(label, str) else member.name)
    return names, labels


def input_parameters(cls, experiment, fixed_kwargs: dict) -> tuple[list, dict]:
    """The parameters of a task's endpoint, and the annotations to go with them.

    Args:
        cls: The task class (a dataclass).
        experiment: The experiment, whose instruments are offered where the task
            names one (`applies_to`).
        fixed_kwargs (dict): Inputs fixed for this registration, which are not
            asked for.

    Returns:
        tuple: The `inspect.Parameter`s, in the dataclass's order, with the ones
            that have defaults after those that don't (as a signature needs), and
            each one's annotation by name.
    """
    try:
        hints = get_type_hints(cls)
    except Exception:  # noqa: BLE001 - fall back on the annotations as written
        hints = {}
    docs = attribute_docs(cls)
    applies_to = getattr(cls, "applies_to", None) or {}
    instruments = getattr(experiment, "instruments", {}) or {}

    required, optional, annotations = [], [], {}
    for field in fields(cls):
        if field.name in fixed_kwargs:
            continue
        hint = hints.get(field.name, field.type)
        enums = enum_classes(hint)
        # An enum is asked for as text, which is resolved to the member.
        kind = str if enums else hint

        extra = {}
        if enums and not _allows_text(hint):
            extra["enum"], extra["x-labels"] = _enum_choices(enums)
        if field.name in applies_to:
            ids = [
                uid
                for uid, instrument in instruments.items()
                if isinstance(instrument, applies_to[field.name])
            ]
            if ids:
                extra["enum"] = ids

        default = Parameter.empty
        if field.default is not MISSING:
            default = field.default
            if isinstance(default, Enum):
                default = default.name

        query = Query(description=docs.get(field.name), json_schema_extra=extra or None)
        annotation = Annotated[kind, query]
        annotations[field.name] = annotation
        parameter = Parameter(
            field.name,
            Parameter.POSITIONAL_OR_KEYWORD,
            annotation=annotation,
            default=default,
        )
        (required if default is Parameter.empty else optional).append(parameter)
    return required + optional, annotations
