import pytest
import time

from pyacquisition.instruments import Clock


pytestmark = pytest.mark.software


@pytest.fixture
def clock():
	return Clock('my_clock')



def test_clock_cache(clock):

	t0 = clock.timestamp_ms()
	time.sleep(1e-3)
	t1 = clock.timestamp_ms(from_cache=True)
	time.sleep(1e-3)
	t2 = clock.timestamp_ms()

	assert t1 == t0
	assert t2 > t1