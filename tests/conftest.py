"""Options for the hardware tests in `tests/hardware`, the slow tests, and the
install check in `tests/install`.

Registered here, at the top of `tests/`, because pytest only reads a command
line option from a conftest it has loaded before parsing.

    pytest tests/hardware --hardware hardware.toml               read-only checks
    pytest tests/hardware --hardware hardware.toml --reversible  also change settings and restore
    pytest tests/hardware --hardware hardware.toml --hazardous   also run hazardous checks
    pytest tests/hardware --hardware hardware.toml --dry-run     contact nothing, print what would be sent

Without `--hardware` every hardware test is skipped, so a plain `pytest` (and
CI) never touches an instrument. Use `-m "not hardware"` to leave them out
altogether.

Tests marked `slow` (a real PyInstaller build) are skipped unless `--slow` is
given. Give it at a spec's last milestone, and whenever freezing has changed:

    pytest tests --slow

Tests marked `install` (the install check) are skipped unless `--install` or
`--install-release` is given. They need the internet. Give one before a
release:

    pytest tests/install --install -rA           the checkout, from wheels alone, on each listed Python
    pytest tests/install --install-release -rA   the newest release on PyPI instead
"""

import os

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--slow",
        action="store_true",
        help="also run the tests marked slow, such as a real PyInstaller build",
    )
    group = parser.getgroup("install", "installing the package on each listed Python")
    group.addoption(
        "--install",
        action="store_true",
        help="also run the install check on the checkout: its wheel, installed from "
        "wheels alone on each listed Python (needs the internet)",
    )
    group.addoption(
        "--install-release",
        action="store_true",
        help="also run the install check on the newest release on PyPI",
    )
    group = parser.getgroup("hardware", "verifying instruments on real hardware")
    group.addoption(
        "--hardware",
        metavar="TOML",
        default=os.environ.get("PYACQ_HARDWARE"),
        help="the hardware inventory to verify (or set PYACQ_HARDWARE). "
        "Without it the hardware tests are skipped.",
    )
    group.addoption(
        "--reversible",
        action="store_true",
        help="also run checks that change a setting and put it back",
    )
    group.addoption(
        "--hazardous",
        action="store_true",
        help="also run hazardous checks (outputs, heaters...); implies --reversible",
    )
    group.addoption(
        "--dry-run",
        action="store_true",
        dest="hardware_dry_run",
        help="contact no instrument; run over a stand-in and print what would be sent",
    )
    group.addoption(
        "--hardware-report",
        metavar="JSON",
        default=None,
        help="write the verification report to this file",
    )


def pytest_configure(config):
    # No test fetches news, or writes the user's news file (core/news.py). The
    # tests of the news set it back for themselves.
    os.environ["PYACQUISITION_NEWS"] = "off"
    config.addinivalue_line(
        "markers",
        "hardware: talks to a physical instrument; skipped unless --hardware is given",
    )
    config.addinivalue_line(
        "markers", "slow: takes a minute or more; skipped unless --slow is given"
    )
    config.addinivalue_line(
        "markers",
        "install: installs the package in fresh environments; skipped unless "
        "--install or --install-release is given",
    )
    if config.getoption("--install") and config.getoption("--install-release"):
        raise pytest.UsageError("give --install or --install-release, not both")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--slow"):
        skip_slow = pytest.mark.skip(reason="a slow test: give --slow to run it")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    if not (config.getoption("--install") or config.getoption("--install-release")):
        skip_install = pytest.mark.skip(reason="an install check: give --install to run it")
        for item in items:
            # The marker, not the keyword: every test in tests/install has the
            # folder's name as a keyword, the ones that always run included.
            if item.get_closest_marker("install"):
                item.add_marker(skip_install)
    if config.getoption("--hardware"):
        return
    skip = pytest.mark.skip(
        reason="hardware tests need --hardware <hardware.toml> (or PYACQ_HARDWARE)"
    )
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip)
