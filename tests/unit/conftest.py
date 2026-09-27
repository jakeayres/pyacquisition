from pathlib import Path

import pytest

from pyacquisition.core.logging import logger

# Where pytest is run from: the repository.
ROOT_LOG = Path("debug.log").resolve()


@pytest.fixture(autouse=True, scope="session")
def nothing_logs_into_the_repository():
    """An experiment made without a `root_path` logs to `debug.log` where it is
    run from, which for the tests is the repository. Give it a temporary folder
    (`tmp_path`), or run the test in one (`monkeypatch.chdir(tmp_path)`)."""
    there_before = ROOT_LOG.exists()
    yield
    assert there_before or not ROOT_LOG.exists(), (
        f"a test wrote {ROOT_LOG}: give its experiment a root_path in tmp_path"
    )


@pytest.fixture(autouse=True)
def forget_log_subscribers():
    """
    Every Experiment subscribes its log websocket to the one global logger, and
    nothing unsubscribes it. Each leftover subscriber makes every later log call
    slower, so a test run that builds many experiments gets slower and slower, and
    timing-based tests become unreliable. Clear them after each test.
    """
    yield
    logger._subscribers.clear()
