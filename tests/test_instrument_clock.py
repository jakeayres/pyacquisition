import pytest
from pyacquisition.instruments import Clock
import time


pytestmark = [
	pytest.mark.software,
]


# Instantiate the Clock class
@pytest.fixture
def clock():
	return Clock('my_clock')


def test_timestamp_ms(clock):
	timestamp = clock.timestamp_ms()
	assert isinstance(timestamp, float)


def test_time(clock):
	clock_time = clock.time()
	assert isinstance(clock_time, float)


def test_start_and_read_named_timer(clock):
	clock.start_named_timer('test_timer')
	time.sleep(0.1)  # sleep for 100 ms
	timer_value = clock.read_named_timer('test_timer')

	# The timer value should be greater than 0.1 as we slept for 100ms
	assert timer_value >= 0.09
	assert timer_value <= 0.11
