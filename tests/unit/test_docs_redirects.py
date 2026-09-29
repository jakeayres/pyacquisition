"""The docs' redirects (zensical.toml): each old page goes to one that is there."""

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CONFIG = tomllib.loads((ROOT / "zensical.toml").read_text(encoding="utf-8"))
REDIRECTS = CONFIG["project"]["plugins"]["redirects"]["redirect_maps"]


@pytest.mark.parametrize("old, new", REDIRECTS.items())
def test_a_redirect_goes_from_a_page_that_is_gone_to_one_that_is_there(old, new):
    assert not (DOCS / old).exists(), f"{old} is a page, which its redirect would hide"
    assert (DOCS / new).exists(), f"{old} goes to {new}, which is not a page"


def test_no_redirect_goes_to_another_redirect():
    chained = {old: new for old, new in REDIRECTS.items() if new in REDIRECTS}
    assert chained == {}
