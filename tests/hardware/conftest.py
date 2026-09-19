import json

import pytest

from pyacquisition.verify import Bench, Hazard, Policy


@pytest.fixture(scope="session")
def bench(request):
    """The instruments of the inventory, opened when first used.

    However the run ends, every instrument that was written to is put back in its
    safe state when this fixture is torn down.
    """
    config = request.config
    limit = Hazard.READ_ONLY
    if config.getoption("--reversible"):
        limit = Hazard.REVERSIBLE
    if config.getoption("--hazardous"):
        limit = Hazard.HAZARDOUS

    bench = Bench(Policy(limit), dry_run=config.getoption("hardware_dry_run"))
    config._hardware_report = bench.report  # for the summary, printed after teardown
    try:
        yield bench
    finally:
        bench.close()
        path = config.getoption("--hardware-report")
        if path:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(bench.report.to_dict(), file, indent=2)


def pytest_terminal_summary(terminalreporter, config):
    report = getattr(config, "_hardware_report", None)
    if report is not None and report.results:
        terminalreporter.write_sep("=", "hardware verification report")
        terminalreporter.write_line(report.text())
