"""Options for the hardware tests in `tests/hardware`.

Registered here, at the top of `tests/`, because pytest only reads a command
line option from a conftest it has loaded before parsing.

    pytest tests/hardware --hardware hardware.toml               read-only checks
    pytest tests/hardware --hardware hardware.toml --reversible  also change settings and restore
    pytest tests/hardware --hardware hardware.toml --hazardous   also run hazardous checks
    pytest tests/hardware --hardware hardware.toml --dry-run     contact nothing, print what would be sent

Without `--hardware` every hardware test is skipped, so a plain `pytest` (and
CI) never touches an instrument. Use `-m "not hardware"` to leave them out
altogether.
"""

import os

import pytest


def pytest_addoption(parser):
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
    config.addinivalue_line(
        "markers",
        "hardware: talks to a physical instrument; skipped unless --hardware is given",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--hardware"):
        return
    skip = pytest.mark.skip(
        reason="hardware tests need --hardware <hardware.toml> (or PYACQ_HARDWARE)"
    )
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip)
