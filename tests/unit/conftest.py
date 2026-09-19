import pytest

from pyacquisition.core.logging import logger


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
