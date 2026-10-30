"""The Pythons the package lists (its `3.N` classifiers), `requires-python`, and
the installation page stay in step. These run with the rest of the suite; the
install check itself is test_install_wheels.py."""

import re

from pythons import ROOT, listed, requires_python

PAGE = ROOT / "docs" / "getting_started" / "installation.md"


def test_the_list_has_no_gaps():
    minors = [int(version.split(".")[1]) for version in listed()]
    assert minors, "pyproject.toml lists no `Programming Language :: Python :: 3.N`"
    assert minors == list(range(minors[0], minors[-1] + 1)), f"a gap in {listed()}"


def test_requires_python_is_the_oldest_listed_with_no_upper_bound():
    # An upper bound doesn't stop uv, which ignores it, and sends pip users back
    # to older releases, whose metadata can't change.
    assert requires_python() == f">={listed()[0]}"


def test_the_installation_page_makes_projects_with_the_newest():
    newest = listed()[-1]
    page = PAGE.read_text(encoding="utf-8")
    inits = re.findall(r"uv init my-lab[^\n`]*", page)
    assert inits, f"{PAGE.name} has no `uv init my-lab`"
    for init in inits:
        assert re.fullmatch(rf"uv init my-lab --python {re.escape(newest)}( .*)?", init.strip()), (
            f"{PAGE.name} has `{init.strip()}`: the newest listed Python is {newest}"
        )
    pins = re.findall(r"uv python pin ([\d.]+)", page)
    assert set(pins) <= {newest}, f"{PAGE.name} pins Python {sorted(set(pins))}: the newest listed is {newest}"
    shown = re.findall(r'requires-python = ">=([\d.]+)"', page)
    assert shown and set(shown) == {newest}, (
        f"{PAGE.name} shows requires-python >= {sorted(set(shown))}: the newest listed Python is {newest}"
    )
