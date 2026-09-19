"""Verifies instrument classes against the instruments that are connected.

One test per check per instrument in the inventory. The plan is built from each
class and its spec, without connecting to anything, so the tests are collected
whether or not the instruments are reachable. An instrument that cannot be
reached makes its tests skip.

Only read-only checks run unless `--reversible` or `--hazardous` is given. See
`tests/conftest.py` for the options, and `hardware.example.toml` for an inventory.
"""

import pytest

from pyacquisition.verify import Bench, Policy, Status, load_inventory

pytestmark = pytest.mark.hardware


def _cases(config):
    path = config.getoption("--hardware")
    if not path:
        return []
    planner = Bench(Policy())  # plans only: nothing is connected
    return [
        (entry, check)
        for entry in load_inventory(path)
        for check in planner.plan(entry)
    ]


def pytest_generate_tests(metafunc):
    if "case" not in metafunc.fixturenames:
        return
    cases = _cases(metafunc.config)
    if not cases:
        metafunc.parametrize("case", [pytest.param(None, id="no-inventory")])
        return
    metafunc.parametrize(
        "case", cases, ids=[f"{e.name}::{c.pytest_id}" for e, c in cases]
    )


def test_instrument(case, bench):
    if case is None:
        pytest.skip("give --hardware hardware.toml (or set PYACQ_HARDWARE)")
    entry, check = case
    result = bench.run(entry, check)

    if result.status is Status.SKIPPED:
        pytest.skip(result.detail)
    if result.status is Status.FAILED:
        sent = "".join(f"\n  > {message}" for message in result.sent)
        pytest.fail(f"{result.detail}{sent}", pytrace=False)
