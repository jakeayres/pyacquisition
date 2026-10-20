"""Every first-party source file in the package starts with the licence notice:
the SPDX identifier, the copyright line and the MPL's Exhibit A, in its own
comment style (specs/archive/relicense-mpl.md). The vendored libraries in
gui/static/vendor/ are other people's, under their own licences."""

from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "pyacquisition"
VENDOR = PACKAGE / "gui" / "static" / "vendor"

LINES = [
    "SPDX-License-Identifier: MPL-2.0",
    "Copyright (C) 2023-2026 Jake Ayres",
    "",
    "This Source Code Form is subject to the terms of the Mozilla Public",
    "License, v. 2.0. If a copy of the MPL was not distributed with this",
    "file, You can obtain one at https://mozilla.org/MPL/2.0/.",
]


def notice(suffix: str) -> str:
    """The notice as a file of this kind starts with it."""
    if suffix == ".py":
        lines = [f"# {line}".rstrip() for line in LINES]
    elif suffix == ".js":
        lines = [f"// {line}".rstrip() for line in LINES]
    elif suffix == ".css":
        lines = [f"/* {LINES[0]}", *(f" * {line}".rstrip() for line in LINES[1:-1]), f" * {LINES[-1]} */"]
    else:  # .html, after its doctype
        lines = ["<!doctype html>", "<!--", *(f"  {line}".rstrip() for line in LINES), "-->"]
    return "\n".join(lines) + "\n"


def sources():
    for path in sorted(PACKAGE.rglob("*")):
        if path.suffix in (".py", ".js", ".css", ".html") and VENDOR not in path.parents:
            if "__pycache__" not in path.parts:
                yield path


def test_there_are_sources_to_check():
    found = {path.suffix for path in sources()}

    assert found == {".py", ".js", ".css", ".html"}


def test_every_first_party_source_file_starts_with_the_notice():
    missing = [
        str(path.relative_to(PACKAGE))
        for path in sources()
        if not path.read_text(encoding="utf-8").replace("\r\n", "\n").startswith(notice(path.suffix))
    ]

    assert missing == [], f"{len(missing)} without the licence notice: {', '.join(missing)}"


def test_the_vendored_libraries_keep_their_own():
    assert not any(
        "SPDX-License-Identifier: MPL-2.0" in path.read_text(encoding="utf-8")
        for path in VENDOR.rglob("*")
        if path.is_file()
    )
